from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from ..models import Event, Task
from .conflicts import ConflictCheck, check_event


@dataclass(frozen=True)
class TakeResult:
    task: Task
    event: Event
    conflict_check: ConflictCheck


def suggestions(user, minutes):
    return (
        Task.objects.filter(  # ty: ignore[unresolved-attribute]
            user=user,
            deadline__isnull=True,
            status=Task.Status.TODO,
            estimated_minutes__lte=minutes,
            scheduled_events__isnull=True,
        )
        .select_related("category")
        .order_by("-priority", "estimated_minutes", "pk")
    )


@transaction.atomic
def take_task(user, task_id, minutes, *, force=False):
    task = Task.objects.select_for_update().get(user=user, pk=task_id)  # ty: ignore[unresolved-attribute]
    if not suggestions(user, minutes).filter(pk=task.pk).exists():
        raise ValidationError(
            "Це завдання вже недоступне або не вкладається у вільний час. Оберіть інше."
        )
    start = timezone.now()
    event = Event(
        user=user,
        source_task=task,
        title=task.title,
        description=task.description,
        category=task.category,
        start=start,
        end=start + timedelta(minutes=task.estimated_minutes),
    )
    event.full_clean()
    conflict_check = check_event(event)
    result = TakeResult(task, event, conflict_check)
    if conflict_check.conflicts and not force:
        return result
    event.save()
    task.status = Task.Status.IN_PROGRESS
    task.save(update_fields=["status"])
    return result
