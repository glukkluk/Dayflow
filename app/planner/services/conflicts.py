"""Conflict checks shared by event forms and calendar updates."""

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone

from ..models import Event
from .recurrence import Occurrence, expand


@dataclass(frozen=True)
class ConflictCheck:
    conflicts: list[Occurrence]
    start: datetime
    end: datetime


def occurrences_in_range(user, start, end, exclude_event_id=None):
    events = (
        Event.objects.filter(user=user, all_day=False, start__lt=end)  # ty: ignore[unresolved-attribute]
        .filter(Q(end__gt=start) | ~Q(recurrence=Event.Recurrence.NONE))
        .exclude(pk=exclude_event_id)
        .select_related("category")
    )
    tz = ZoneInfo(user.profile.timezone)
    return [item for event in events for item in expand(event, start, end, tz=tz)]


def find_conflicts(user, start, end, exclude_event_id=None):
    """Half-open intervals: touching endpoints are not conflicts."""
    if timezone.is_naive(start) or timezone.is_naive(end) or end <= start:
        raise ValueError("Invalid conflict range.")
    return sorted(
        occurrences_in_range(user, start, end, exclude_event_id),
        key=lambda item: (item.start, item.event.pk),
    )


def check_event(event, *, now=None):
    """Finite series: all occurrences. Open series: 365 days from start/now."""
    tz = ZoneInfo(event.user.profile.timezone)
    start, end = event.start.astimezone(UTC), event.end.astimezone(UTC)
    if event.recurrence != Event.Recurrence.NONE:
        if event.recurrence_until:
            end = datetime.combine(
                event.recurrence_until + timedelta(days=1), time.min, tzinfo=tz
            ).astimezone(UTC)
        else:
            start = max(start, now or timezone.now())
            end = start + timedelta(days=365)
    proposed = expand(event, start, end, tz=tz)
    if not proposed or event.all_day:
        return ConflictCheck([], start, end)
    others = occurrences_in_range(
        event.user,
        min(item.start for item in proposed),
        max(item.end for item in proposed),
        event.pk,
    )
    starts = sorted(item.start for item in proposed)
    ends = sorted(item.end for item in proposed)
    # Count intervals starting before B.end minus those ending before B.start.
    conflicts = [
        item
        for item in others
        if bisect_left(starts, item.end) > bisect_right(ends, item.start)
    ]
    conflicts.sort(key=lambda item: (item.start, item.event.pk))
    return ConflictCheck(conflicts, start, end)
