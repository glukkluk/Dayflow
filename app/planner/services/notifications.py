"""In-app reminders: generate rows for due events and task deadlines.

Delivery is pull-based: the UI polls the pending endpoint, so no cron is
needed. Generation is idempotent — a notification exists at most once per
event occurrence or task deadline (unique constraints + pre-check), so
repeated polls or overlapping occurrences never duplicate reminders.

Precision is limited to one collection window (≈1 minute), matching the
poll cadence; reminders are never silently skipped inside the window.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import Event, Notification, Task
from .recurrence import OccurrenceTimeError, expand

# Longest supported reminder lead time (1 day).
MAX_REMINDER = timedelta(minutes=1440)
DEADLINE_REMINDER = timedelta(hours=24)
COLLECTION_WINDOW = timedelta(minutes=1)


def _format_time(value, tz):
    return timezone.localtime(value, tz).strftime("%d.%m.%Y %H:%M")


def _event_message(event, occurrence_start, tz, now):
    start = timezone.localtime(occurrence_start, tz)
    delta = occurrence_start - now
    if delta >= timedelta(hours=23):
        lead = "завтра"
    elif delta >= timedelta(minutes=90):
        lead = f"за {delta.seconds // 3600} год"
    elif delta >= timedelta(minutes=2):
        lead = f"за {delta.seconds // 60} хв"
    else:
        lead = "незабаром"
    return f"Подія «{event.title}» почнеться {lead} (о {start.strftime('%H:%M')})."


def _deadline_message(task, tz):
    return (
        f"Дедлайн завдання «{task.title}» — за 24 год "
        f"({_format_time(task.deadline, tz)})."
    )


def _create(notification):
    """Insert ignoring races: a duplicate means another poll already sent it."""
    try:
        with transaction.atomic():
            notification.save()
    except IntegrityError:
        return None
    return notification


def collect_event_reminders(user, now=None):
    """Notify about series instances starting within reminder_minutes."""
    now = now or timezone.now()
    tz = ZoneInfo(user.profile.timezone)
    window_start, window_end = now - COLLECTION_WINDOW, now + COLLECTION_WINDOW
    horizon = now + MAX_REMINDER + COLLECTION_WINDOW
    notifications = []
    events = (
        Event.objects.filter(user=user, reminder_minutes__isnull=False)  # ty: ignore[unresolved-attribute]
        .exclude(recurrence=Event.Recurrence.NONE, start__lt=now - COLLECTION_WINDOW)
        .select_related("category")
    )
    for event in events:
        # Reminders exist for the future: a series already running (or a
        # one-off in the past) gets none, even if a later instance is due.
        if event.recurrence == Event.Recurrence.NONE and event.start <= window_start:
            continue
        try:
            occurrences = expand(event, window_start, horizon, tz=tz)
        except OccurrenceTimeError:
            # An invalid occurrence (e.g. inside a DST gap) simply yields
            # no reminder; the series remains fixable from the dashboard.
            continue
        for occurrence in occurrences:
            remind_at = occurrence.start - timedelta(minutes=event.reminder_minutes)
            if not window_start <= remind_at <= window_end:
                continue
            existing = Notification.objects.filter(  # ty: ignore[unresolved-attribute]
                event=event, occurrence_start=occurrence.start
            ).exists()
            if existing:
                continue
            notification = Notification(
                user=user,
                event=event,
                occurrence_start=occurrence.start,
                kind=Notification.Kind.EVENT,
                message=_event_message(event, occurrence.start, tz, now),
            )
            created = _create(notification)
            if created is not None:
                notifications.append(created)
    return notifications


def collect_deadline_reminders(user, now=None):
    """Notify once about unfinished tasks 24 hours before the deadline."""
    now = now or timezone.now()
    tz = ZoneInfo(user.profile.timezone)
    remind_at = now + DEADLINE_REMINDER
    window_start = remind_at - COLLECTION_WINDOW
    window_end = remind_at + COLLECTION_WINDOW
    notifications = []
    tasks = Task.objects.filter(  # ty: ignore[unresolved-attribute]
        user=user,
        status__in=(Task.Status.TODO, Task.Status.IN_PROGRESS),
        deadline__isnull=False,
        deadline__gte=window_start,
        deadline__lte=window_end,
    )
    for task in tasks:
        if Notification.objects.filter(  # ty: ignore[unresolved-attribute]
            task=task, kind=Notification.Kind.DEADLINE
        ).exists():
            continue
        notification = Notification(
            user=user,
            task=task,
            kind=Notification.Kind.DEADLINE,
            message=_deadline_message(task, tz),
        )
        created = _create(notification)
        if created is not None:
            notifications.append(created)
    return notifications


def collect_due(user, now=None):
    """Create all reminders due around `now`; return the created rows."""
    return collect_event_reminders(user, now) + collect_deadline_reminders(user, now)


def unread_count(user):
    return Notification.objects.filter(user=user, read_at__isnull=True).count()  # ty: ignore[unresolved-attribute]


def serialize(notification):
    return {
        "id": notification.pk,
        "kind": notification.kind,
        "kind_display": notification.get_kind_display(),
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at.isoformat(),
        "event_id": notification.event_id,
        "task_id": notification.task_id,
        "occurrence_start": (
            notification.occurrence_start.isoformat()
            if notification.occurrence_start
            else None
        ),
    }
