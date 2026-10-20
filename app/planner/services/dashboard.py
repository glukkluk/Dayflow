"""Read-only dashboard summaries in the profile's local day and week."""

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.utils import timezone

from ..models import Category, Event, Task
from .recurrence import Occurrence, OccurrenceTimeError, _utc_candidates, expand


@dataclass(frozen=True)
class TodayEvent:
    occurrence: Occurrence
    is_current: bool


@dataclass(frozen=True)
class CategoryTime:
    name: str
    color: str
    minutes: int

    @property
    def hours(self):
        return self.minutes // 60

    @property
    def remaining_minutes(self):
        return self.minutes % 60


def _midnight(day, tz):
    candidates = _utc_candidates(datetime.combine(day, time.min), tz)
    if len(candidates) != 1:
        raise ValidationError(
            "Межа дня у вибраному часовому поясі не існує або є неоднозначною. "
            "Перевірте часовий пояс профілю."
        )
    return candidates[0]


def summarize(user, *, now=None):
    now = now or timezone.now()
    if timezone.is_naive(now):
        raise ValueError("Dashboard time must include a timezone.")
    now = now.astimezone(UTC)
    tz = ZoneInfo(user.profile.timezone)
    today = now.astimezone(tz).date()
    monday = today - timedelta(days=today.weekday())
    day_start, day_end = _midnight(today, tz), _midnight(today + timedelta(days=1), tz)
    week_start, week_end = (
        _midnight(monday, tz),
        _midnight(monday + timedelta(days=7), tz),
    )

    tasks = Task.objects.filter(user=user)  # ty: ignore[unresolved-attribute]
    weekly = tasks.filter(deadline__gte=week_start, deadline__lt=week_end).aggregate(
        total=Count("pk"),
        done=Count("pk", filter=Q(status=Task.Status.DONE)),
    )
    task_status = tasks.aggregate(
        total=Count("pk"),
        done=Count("pk", filter=Q(status=Task.Status.DONE)),
        in_progress=Count("pk", filter=Q(status=Task.Status.IN_PROGRESS)),
        todo=Count("pk", filter=Q(status=Task.Status.TODO)),
    )
    unfinished = tasks.exclude(status=Task.Status.DONE)
    deadlines = list(
        unfinished.filter(deadline__gte=now).order_by("deadline", "pk")[:3]
    )
    overdue_count = unfinished.filter(deadline__lt=now).count()

    events = (
        Event.objects.filter(user=user, start__lt=week_end)  # ty: ignore[unresolved-attribute]
        .filter(Q(end__gt=week_start) | ~Q(recurrence=Event.Recurrence.NONE))
        .select_related("category")
    )
    today_events = []
    weekly_event_count = 0
    category_seconds = {}
    categories = {}
    errors = []
    for event in events:
        try:
            weekly_occurrences = expand(event, week_start, week_end, tz=tz)
        except OccurrenceTimeError as error:
            errors.append({"event": event, "message": error.messages[0]})
            try:
                today_occurrences = expand(event, day_start, day_end, tz=tz)
            except OccurrenceTimeError:
                today_occurrences = []
            weekly_occurrences = []
        else:
            today_occurrences = [
                item
                for item in weekly_occurrences
                if item.start < day_end and item.end > day_start
            ]
        today_events.extend(
            TodayEvent(item, item.start <= now < item.end) for item in today_occurrences
        )
        weekly_event_count += len(weekly_occurrences)
        if event.all_day:
            continue
        for item in weekly_occurrences:
            seconds = (
                min(item.end, week_end) - max(item.start, week_start)
            ).total_seconds()
            key = event.category_id
            category_seconds[key] = category_seconds.get(key, 0) + seconds
            categories[key] = event.category

    today_events.sort(
        key=lambda item: (item.occurrence.start, item.occurrence.event.pk)
    )
    category_times = [
        CategoryTime(
            categories[key].name if categories[key] else "Без категорії",
            categories[key].color if categories[key] else "#6B7280",
            int(seconds // 60),
        )
        for key, seconds in category_seconds.items()
    ]
    category_times.sort(key=lambda item: (-item.minutes, item.name))
    current_events = sum(item.is_current for item in today_events)
    upcoming_events = sum(item.occurrence.start > now for item in today_events)
    category_total = Category.objects.filter(user=user).count()  # ty: ignore[unresolved-attribute]
    return {
        "dashboard_now": now,
        "today": today,
        "week_start_date": monday,
        "week_end_date": monday + timedelta(days=6),
        "today_events": today_events,
        "today_event_count": len(today_events),
        "current_event_count": current_events,
        "upcoming_event_count": upcoming_events,
        "weekly_event_count": weekly_event_count,
        "nearest_deadlines": deadlines,
        "overdue_count": overdue_count,
        "task_status": task_status,
        "unfinished_count": task_status["total"] - task_status["done"],
        "weekly_total": weekly["total"],
        "weekly_done": weekly["done"],
        "weekly_percent": (
            round(100 * weekly["done"] / weekly["total"]) if weekly["total"] else 0
        ),
        "category_times": category_times,
        "category_total": category_total,
        "category_used_count": len(
            [key for key in category_seconds if key is not None]
        ),
        "categorized_hours": sum(item.minutes for item in category_times) // 60,
        "categorized_remaining_minutes": sum(item.minutes for item in category_times)
        % 60,
        "categorized_minutes": sum(item.minutes for item in category_times),
        "recurrence_errors": errors,
    }
