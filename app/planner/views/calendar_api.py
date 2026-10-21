import json
from datetime import UTC, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View

from ..models import Event
from ..services.conflicts import check_event, find_conflicts
from ..services.event_moves import apply_move
from ..services.recurrence import OccurrenceTimeError, expand


def parse_range(params):
    try:
        start = parse_datetime(params.get("start", ""))
        end = parse_datetime(params.get("end", ""))
        if (
            start is None
            or end is None
            or timezone.is_naive(start)
            or timezone.is_naive(end)
        ):
            raise ValueError

        start, end = start.astimezone(UTC), end.astimezone(UTC)
        if not timedelta(0) < end - start <= timedelta(days=366):
            raise ValueError

    except ValueError, OverflowError:
        raise ValueError(
            "Вкажіть start і end у форматі ISO з часовим поясом. "
            "Кінець має бути пізніше початку; діапазон — не більше 366 днів."
        ) from None

    return start, end


def serialize_occurrence(occurrence, tz):
    event = occurrence.event
    start, end = occurrence.start.astimezone(tz), occurrence.end.astimezone(tz)

    if event.all_day:
        end_date = end.date()
        if end.time() != time.min:
            end_date += timedelta(days=1)
        start_value, end_value = start.date().isoformat(), end_date.isoformat()
    else:
        start_value, end_value = start.isoformat(), end.isoformat()

    return {
        "id": str(event.pk),
        "title": event.title,
        "start": start_value,
        "end": end_value,
        "color": event.category.color if event.category else "#6B7280",
        "allDay": event.all_day,
        "extendedProps": {
            "description": event.description,
            "occurrence_start": occurrence.start.isoformat(),
            "move_url": reverse("planner:event_move", args=[event.pk]),
            "detail_url": reverse("planner:event_detail", args=[event.pk]),
            "edit_url": reverse("planner:event_edit", args=[event.pk]),
            "delete_url": reverse("planner:event_delete", args=[event.pk]),
            "category": event.category.name if event.category else None,
            "is_recurring": event.recurrence != Event.Recurrence.NONE,
            "source_task": event.source_task_id,
        },
    }


class CalendarEventsView(LoginRequiredMixin, View):
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        try:
            range_start, range_end = parse_range(request.GET)

        except ValueError as error:
            return JsonResponse({"error": str(error)}, status=400)

        tz = ZoneInfo(request.user.profile.timezone)
        events = (
            Event.objects.filter(user=request.user, start__lt=range_end)  # ty: ignore[unresolved-attribute]
            .filter(Q(end__gt=range_start) | ~Q(recurrence=Event.Recurrence.NONE))
            .select_related("category")
        )
        occurrences = []
        try:
            for event in events:
                occurrences.extend(expand(event, range_start, range_end, tz=tz))

        except OccurrenceTimeError as error:
            return JsonResponse(
                {
                    "error": error.messages[0],
                    "code": error.code,
                    "event_id": error.event_id,
                },
                status=400,
            )

        occurrences.sort(key=lambda occurrence: (occurrence.start, occurrence.event.pk))
        return JsonResponse(
            [serialize_occurrence(item, tz) for item in occurrences], safe=False
        )


def read_json(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValidationError("Очікується JSON-об'єкт.")
        return data

    except ValueError, UnicodeDecodeError:
        raise ValidationError("Очікується JSON-об'єкт.") from None


def parse_instant(value):
    try:
        parsed = parse_datetime(value) if isinstance(value, str) else None
        if parsed is None or timezone.is_naive(parsed):
            raise ValueError
        return parsed.astimezone(UTC)

    except ValueError, OverflowError:
        raise ValidationError("Дата й час мають містити часовий пояс.") from None


def conflict_payload(items, tz):
    return [
        {
            "id": item.event.pk,
            "title": item.event.title,
            "start": item.start.astimezone(tz).isoformat(),
            "end": item.end.astimezone(tz).isoformat(),
        }
        for item in items
    ]


class EventMoveView(LoginRequiredMixin, View):
    http_method_names = ["patch", "options"]

    def patch(self, request, pk):
        with transaction.atomic():
            event = get_object_or_404(
                Event.objects.select_for_update(),  # ty: ignore[unresolved-attribute]
                user=request.user,
                pk=pk,
            )
            event.user = request.user
            try:
                data = read_json(request)
                if type(data.get("force", False)) is not bool:
                    raise ValidationError("force має бути логічним значенням.")
                start, end = (
                    parse_instant(data.get("start")),
                    parse_instant(data.get("end")),
                )
                if end <= start:
                    raise ValidationError("Кінець події має бути пізніше за початок.")
                occurrence = (
                    parse_instant(data["occurrence_start"])
                    if "occurrence_start" in data
                    else None
                )
                apply_move(event, start, end, occurrence)
                result = check_event(event)

            except (ValidationError, ValueError, OverflowError) as error:
                errors = (
                    error.messages
                    if isinstance(error, ValidationError)
                    else ["Некоректний діапазон дат."]
                )
                return JsonResponse({"errors": errors}, status=400)

            tz = ZoneInfo(request.user.profile.timezone)
            if result.conflicts and not data.get("force", False):
                return JsonResponse(
                    {
                        "conflicts": conflict_payload(result.conflicts, tz),
                        "checked_start": result.start.isoformat(),
                        "checked_end": result.end.isoformat(),
                    },
                    status=409,
                )
            event.save()

        return JsonResponse(
            {
                "id": event.pk,
                "start": event.start.isoformat(),
                "end": event.end.isoformat(),
            }
        )


class CheckConflictsView(LoginRequiredMixin, View):
    http_method_names = ["post", "options"]

    def post(self, request):
        try:
            data = read_json(request)
            start, end = (
                parse_instant(data.get("start")),
                parse_instant(data.get("end")),
            )
            exclude = data.get("exclude_id")
            if exclude is not None:
                if type(exclude) is not int:
                    raise ValidationError("exclude_id має бути цілим числом.")
                get_object_or_404(Event, pk=exclude, user=request.user)
            if not timedelta(0) < end - start <= timedelta(days=366):
                raise ValidationError(
                    "Діапазон має бути додатним і не перевищувати 366 днів."
                )
            conflicts = find_conflicts(request.user, start, end, exclude)
        except (ValidationError, ValueError, OverflowError) as error:
            errors = (
                error.messages
                if isinstance(error, ValidationError)
                else ["Некоректний діапазон дат."]
            )
            return JsonResponse({"errors": errors}, status=400)
        return JsonResponse(
            {
                "conflicts": conflict_payload(
                    conflicts, ZoneInfo(request.user.profile.timezone)
                )
            }
        )
