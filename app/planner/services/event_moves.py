from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError

from ..models import Event
from .recurrence import OccurrenceTimeError, _utc_candidates, expand


def apply_move(event, start, end, occurrence_start=None):
    """Change an unsaved event; dragging an occurrence shifts the series anchor."""
    tz = ZoneInfo(event.user.profile.timezone)

    def strict(value):
        candidates = _utc_candidates(value, tz)
        if len(candidates) != 1:
            raise OccurrenceTimeError(event, value)
        return candidates[0]

    local_start = start.astimezone(tz).replace(tzinfo=None)
    local_end = end.astimezone(tz).replace(tzinfo=None)
    strict(local_start)
    strict(local_end)
    if event.recurrence != Event.Recurrence.NONE:
        if occurrence_start is None:
            raise ValidationError("Для зміни серії передайте occurrence_start.")
        occurrences = expand(
            event, occurrence_start, occurrence_start + timedelta(microseconds=1), tz=tz
        )
        if not any(item.start == occurrence_start for item in occurrences):
            raise ValidationError("Екземпляр серії змінився. Оновіть календар.")
        delta = local_start - occurrence_start.astimezone(tz).replace(tzinfo=None)
        anchor = event.start.astimezone(tz).replace(tzinfo=None) + delta
        event.start = strict(anchor)
        event.end = strict(anchor + (local_end - local_start))
    else:
        event.start, event.end = start, end
    event.full_clean()
