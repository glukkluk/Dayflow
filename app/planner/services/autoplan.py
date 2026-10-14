"""Deterministic auto-scheduling of todo tasks into work-hour gaps.

Algorithm (per FR-7 / section 8.3 of the requirements):
- candidates: status=todo with an estimate and no linked events yet;
- order: priority high-first, then nearest deadline (no deadline last),
  then shorter estimate;
- horizon: now .. deadline, or now + 14 days without a deadline;
- each day contributes its [work_start, work_end] window in the profile
  timezone (today starts at max(now, work_start) rounded up to 5 minutes);
- busy intervals are existing occurrences (including recurring series and
  all-day events, which block the whole day) plus blocks already placed in
  this run; existing events are padded with the profile buffer on both
  sides, placed blocks carry a trailing buffer, so every boundary between
  two blocks holds exactly one buffer;
- greedy fill of the earliest gaps; a task longer than one gap is split
  into blocks of at least 25 minutes whose sum equals the estimate;
- a task that does not fit is rolled back and reported as failed;
- Event rows are created only by apply_plan(), inside one transaction,
  after the user confirms the preview.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from ..models import Event, Task
from .recurrence import _utc_candidates, expand

MIN_BLOCK_MINUTES = 25
ROUND_MINUTES = 5
DEFAULT_HORIZON_DAYS = 14

NO_SLOT_BEFORE_DEADLINE = "no_slot_before_deadline"
NO_WORKING_HOURS = "no_working_hours"


@dataclass(frozen=True)
class Block:
    task: Task
    start: datetime  # UTC
    end: datetime  # UTC


@dataclass(frozen=True)
class Failure:
    task: Task
    reason: str


@dataclass(frozen=True)
class PlanResult:
    placed: tuple[Block, ...] = ()
    failed: tuple[Failure, ...] = ()


def _ceil_to_grid(value: datetime, minutes: int) -> datetime:
    value = value.replace(second=0, microsecond=0)
    remainder = value.minute % minutes
    if remainder:
        value += timedelta(minutes=minutes - remainder)
    return value


def _day_window(tz, day, work_start, work_end, earliest):
    """UTC working window for one local day, or None when unusable.

    A day is skipped (rather than silently shifted) when its local
    boundaries are ambiguous or nonexistent due to a DST transition.
    """
    starts = _utc_candidates(datetime.combine(day, work_start), tz)
    ends = _utc_candidates(datetime.combine(day, work_end), tz)
    if len(starts) != 1 or len(ends) != 1:
        return None
    start, end = starts[0], ends[0]
    if end <= start:
        return None
    if earliest is not None and start < earliest:
        start = earliest
    return (start, end) if start < end else None


def _busy_intervals(user, start, end):
    """Existing occurrences as sorted UTC (start, end) pairs.

    Unlike conflict checks, all-day events are included: they block the
    whole day, so work is not scheduled on top of them.
    """
    events = (
        Event.objects.filter(user=user, start__lt=end)  # ty: ignore[unresolved-attribute]
        .filter(Q(end__gt=start) | ~Q(recurrence=Event.Recurrence.NONE))
        .select_related("category")
    )
    tz = ZoneInfo(user.profile.timezone)
    busy = [
        (item.start, item.end)
        for event in events
        for item in expand(event, start, end, tz=tz)
    ]
    busy.sort()
    return busy


def _subtract(window, busy):
    """Free half-open gaps of `window` after removing sorted `busy` spans."""
    start, end = window
    gaps = []
    cursor = start
    for busy_start, busy_end in busy:
        if busy_end <= cursor or busy_start >= end:
            continue
        if busy_start > cursor:
            gaps.append((cursor, min(busy_start, end)))
        cursor = max(cursor, busy_end)
        if cursor >= end:
            break
    if cursor < end:
        gaps.append((cursor, end))
    return gaps


def _take_minutes(remaining, gap_start, gap_end):
    """Minutes to place in this gap, or None to skip it.

    Whole remainder fits -> take it (covers estimates below 25 minutes).
    Otherwise take the whole gap, except when that would leave a sliver
    below 25 minutes: then shrink this block so 25 minutes remain, or skip
    the gap when even that is impossible.
    """
    gap = int((gap_end - gap_start).total_seconds() // 60)
    if remaining <= gap:
        return remaining
    if gap < MIN_BLOCK_MINUTES:
        return None
    if remaining - gap < MIN_BLOCK_MINUTES:
        if remaining < 2 * MIN_BLOCK_MINUTES:
            return None
        return remaining - MIN_BLOCK_MINUTES
    return gap


def _place(task, *, tz, work_start, work_end, buffer, busy, extra, now):
    """Greedy blocks for one task; ([Block], None) or (None, reason)."""
    horizon_end = task.deadline or (now + timedelta(days=DEFAULT_HORIZON_DAYS))
    if horizon_end <= now:
        return None, NO_SLOT_BEFORE_DEADLINE
    remaining = task.estimated_minutes
    blocks: list[Block] = []
    had_window = False
    today = now.astimezone(tz).date()
    earliest_today = _ceil_to_grid(now, ROUND_MINUTES)
    day = today
    while day <= horizon_end.astimezone(tz).date():
        window = _day_window(
            tz, day, work_start, work_end, earliest_today if day == today else None
        )
        if window is not None:
            window = (window[0], min(window[1], horizon_end))
        if window is not None and window[0] < window[1]:
            had_window = True
            day_busy = [
                (max(start - buffer, window[0]), min(end + buffer, window[1]))
                for start, end in busy
                if start < window[1] and end > window[0]
            ]
            day_busy += [
                (start, min(end, window[1]))
                for start, end in extra
                if start < window[1] and end > window[0]
            ]
            day_busy.sort()
            for gap_start, gap_end in _subtract(window, day_busy):
                if remaining <= 0:
                    break
                take = _take_minutes(remaining, gap_start, gap_end)
                if take is None:
                    continue
                blocks.append(
                    Block(task, gap_start, gap_start + timedelta(minutes=take))
                )
                remaining -= take
        if remaining <= 0:
            break
        day += timedelta(days=1)
    if remaining > 0:
        reason = NO_WORKING_HOURS if not had_window else NO_SLOT_BEFORE_DEADLINE
        return None, reason
    return blocks, None


def plan(user, now=None) -> PlanResult:
    """Compute proposed blocks without writing anything to the database."""
    now = now or timezone.now()
    profile = user.profile
    tz = ZoneInfo(profile.timezone)
    buffer = timedelta(minutes=profile.buffer_minutes)
    candidates = list(
        Task.objects.filter(  # ty: ignore[unresolved-attribute]
            user=user, status=Task.Status.TODO, estimated_minutes__isnull=False
        )
        .filter(scheduled_events__isnull=True)
        .select_related("category")
        .order_by(
            "-priority",
            F("deadline").asc(nulls_last=True),
            "estimated_minutes",
            "pk",
        )
    )
    if not candidates:
        return PlanResult()
    busy_end = now + timedelta(days=DEFAULT_HORIZON_DAYS)
    deadlines = [task.deadline for task in candidates if task.deadline]
    if deadlines:
        busy_end = max([busy_end, *deadlines])
    busy = _busy_intervals(user, now, busy_end)
    placed: list[Block] = []
    extra: list[tuple[datetime, datetime]] = []
    failed: list[Failure] = []
    for task in candidates:
        blocks, reason = _place(
            task,
            tz=tz,
            work_start=profile.work_start,
            work_end=profile.work_end,
            buffer=buffer,
            busy=busy,
            extra=extra,
            now=now,
        )
        if blocks is None:
            failed.append(Failure(task, reason or NO_SLOT_BEFORE_DEADLINE))
            continue
        placed.extend(blocks)
        # Trailing buffer only: the leading side is already covered by the
        # padded existing event or the previous block's trailing buffer.
        extra.extend((block.start, block.end + buffer) for block in blocks)
        extra.sort()
    return PlanResult(tuple(placed), tuple(failed))


def apply_plan(user, result: PlanResult) -> list[Event]:
    """Create one Event per block in a single transaction (all or nothing)."""
    with transaction.atomic():
        events = []
        for block in result.placed:
            event = Event(
                user=user,
                title=block.task.title,
                description=block.task.description,
                start=block.start,
                end=block.end,
                category=block.task.category,
                source_task=block.task,
            )
            event.full_clean()
            events.append(event)
        Event.objects.bulk_create(events)  # ty: ignore[unresolved-attribute]
    return events
