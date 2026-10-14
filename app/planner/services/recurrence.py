"""Expand series in local wall time, returning UTC occurrences in [start, end)."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import Event


class OccurrenceTimeError(ValidationError):
    def __init__(self, event, local_time):
        self.event_id = event.pk
        super().__init__(
            "Подія «%(title)s»: локальний час %(time)s не існує або є неоднозначним. "
            "Змініть час серії чи дату завершення повторень.",
            code="invalid_occurrence_time",
            params={"title": event.title, "time": local_time.isoformat(sep=" ")},
        )


@dataclass(frozen=True)
class Occurrence:
    event: Event
    start: datetime
    end: datetime


@lru_cache(maxsize=4096)
def _utc_candidates(value, tz):
    """Different fold offsets identify both gaps and ambiguous ZoneInfo times."""
    first = value.replace(tzinfo=tz, fold=0)
    second = value.replace(tzinfo=tz, fold=1)
    if first.utcoffset() == second.utcoffset():
        return (first.astimezone(UTC),)
    return first.astimezone(UTC), second.astimezone(UTC)


def _start_at(anchor, recurrence, index):
    if recurrence == Event.Recurrence.MONTHLY:
        month_index = anchor.year * 12 + anchor.month - 1 + index
        year, month = divmod(month_index, 12)
        month += 1
        day = min(anchor.day, monthrange(year, month)[1])
        return anchor.replace(year=year, month=month, day=day)
    step = 7 if recurrence == Event.Recurrence.WEEKLY else 1
    return anchor + timedelta(days=step * index)


def expand(event, range_start, range_end, *, tz: ZoneInfo):
    """Keep local start/end times; recurrence_until includes local start dates.

    Each monthly date is calculated from the original anchor, avoiding drift
    after February. The initial index skips old occurrences outside the range.
    """
    if timezone.is_naive(range_start) or timezone.is_naive(range_end):
        raise ValueError("Range boundaries must include a timezone.")
    range_start, range_end = range_start.astimezone(UTC), range_end.astimezone(UTC)
    if range_end <= range_start:
        raise ValueError("Range end must be after start.")
    start, end = event.start.astimezone(UTC), event.end.astimezone(UTC)
    if event.recurrence == Event.Recurrence.NONE:
        return (
            [Occurrence(event, start, end)]
            if start < range_end and end > range_start
            else []
        )
    if event.recurrence not in Event.Recurrence.values:
        raise ValueError("Unknown recurrence type.")
    if start >= range_end:
        return []

    anchor = start.astimezone(tz).replace(tzinfo=None)
    duration = end.astimezone(tz).replace(tzinfo=None) - anchor
    if duration <= timedelta(0):
        raise OccurrenceTimeError(event, anchor)
    # A margin covers offset changes near the window boundaries.
    try:
        earliest = (
            range_start.astimezone(tz).replace(tzinfo=None)
            - duration
            - timedelta(days=2)
        )
    except OverflowError:
        earliest = datetime.min
    if event.recurrence == Event.Recurrence.MONTHLY:
        index = max(
            0, (earliest.year - anchor.year) * 12 + earliest.month - anchor.month - 1
        )
    else:
        step = 7 if event.recurrence == Event.Recurrence.WEEKLY else 1
        index = max(0, (earliest - anchor).days // step)
    local_limit = range_end.astimezone(tz).replace(tzinfo=None)
    occurrences = []
    while True:
        try:
            local_start = _start_at(anchor, event.recurrence, index)
        except OverflowError, ValueError:
            break  # The next occurrence lies beyond datetime's supported years.
        if local_start.date().toordinal() > local_limit.date().toordinal() + 1:
            break
        if event.recurrence_until and local_start.date() > event.recurrence_until:
            break
        local_end = local_start + duration
        # Compare in UTC, even if a boundary falls inside the repeated DST hour.
        # These bounds only discard unrelated instances; actual times are still
        # validated strictly below, so no fold is silently selected.
        starts = _utc_candidates(local_start, tz)
        ends = _utc_candidates(local_end, tz)
        if min(starts) < range_end and max(ends) > range_start:
            if len(starts) != 1:
                raise OccurrenceTimeError(event, local_start)
            if len(ends) != 1:
                raise OccurrenceTimeError(event, local_end)
            occurrence_start, occurrence_end = starts[0], ends[0]
            if occurrence_end <= occurrence_start:
                raise OccurrenceTimeError(event, local_end)
            if occurrence_start < range_end and occurrence_end > range_start:
                occurrences.append(Occurrence(event, occurrence_start, occurrence_end))
        index += 1
    return occurrences
