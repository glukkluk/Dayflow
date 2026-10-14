from datetime import UTC, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views import View

from ..models import Event
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
            "category": event.category.name if event.category else None,
            "is_recurring": event.recurrence != Event.Recurrence.NONE,
            "source_task": None,
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
