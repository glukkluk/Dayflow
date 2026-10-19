from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField("Назва", max_length=50)
    color = models.CharField(
        "Колір",
        max_length=7,
        default="#3B82F6",
        validators=[
            RegexValidator(
                regex=r"\A#[0-9a-fA-F]{6}\Z",
                message="Вкажіть колір у форматі #RRGGBB.",
            )
        ],
    )

    class Meta:
        ordering = ("name", "pk")
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"
        constraints = [
            models.UniqueConstraint(
                fields=("user", "name"),
                name="category_unique_user_name",
            )
        ]

    def __str__(self):
        return self.name


class Event(models.Model):
    class Recurrence(models.TextChoices):
        NONE = "none", "Не повторюється"
        DAILY = "daily", "Щодня"
        WEEKLY = "weekly", "Щотижня"
        MONTHLY = "monthly", "Щомісяця"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField("Назва", max_length=200)
    description = models.TextField("Опис", blank=True)
    start = models.DateTimeField("Початок")
    end = models.DateTimeField("Кінець")
    all_day = models.BooleanField("Весь день", default=False)
    recurrence = models.CharField(
        "Повторення",
        max_length=7,
        choices=Recurrence.choices,
        default=Recurrence.NONE,
    )
    recurrence_until = models.DateField(
        "Повторювати до",
        null=True,
        blank=True,
        help_text="Включно з цією датою у часовому поясі профілю. Порожнє поле — без кінцевої дати.",
    )
    reminder_minutes = models.PositiveIntegerField(
        "Нагадування за",
        null=True,
        blank=True,
        choices=(
            (5, "5 хвилин"),
            (15, "15 хвилин"),
            (30, "30 хвилин"),
            (60, "1 година"),
            (1440, "1 день"),
            (4320, "3 дні"),
            (10080, "1 тиждень"),
        ),
        help_text="За скільки до початку події показати сповіщення. Порожнє поле — без нагадування.",
    )
    category = models.ForeignKey(
        Category,
        verbose_name="Категорія",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source_task = models.ForeignKey(
        "Task",
        verbose_name="Завдання-джерело",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scheduled_events",
        help_text="Заповнюється автоплануванням; видалення завдання видаляє й ці події.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("start", "pk")
        verbose_name = "Подія"
        verbose_name_plural = "Події"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end__gt=models.F("start")),
                name="event_end_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    recurrence__in=("none", "daily", "weekly", "monthly")
                ),
                name="event_valid_recurrence",
            ),
            models.CheckConstraint(
                condition=~models.Q(recurrence="none")
                | models.Q(recurrence_until__isnull=True),
                name="event_until_requires_recurrence",
            ),
            models.CheckConstraint(
                condition=models.Q(reminder_minutes__isnull=True)
                | models.Q(reminder_minutes__in=(5, 15, 30, 60, 1440, 4320, 10080)),
                name="event_valid_reminder_minutes",
            ),
        ]
        indexes = [
            models.Index(fields=("user", "start"), name="event_user_start_idx"),
            models.Index(fields=("user", "end"), name="event_user_end_idx"),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.start and self.end and self.end <= self.start:
            errors["end"] = "Кінець події має бути пізніше за початок."
        if (
            self.category_id and self.category.user_id != self.user_id  # ty: ignore[unresolved-attribute]
        ):
            errors["category"] = "Виберіть власну категорію."
        if (
            self.source_task_id and self.source_task.user_id != self.user_id  # ty: ignore[unresolved-attribute]
        ):
            errors["source_task"] = "Завдання належить іншому користувачеві."
        if self.recurrence_until:
            if self.recurrence == self.Recurrence.NONE:
                errors["recurrence_until"] = "Спочатку виберіть тип повторення."
            elif self.start and self.user_id:  # ty: ignore[unresolved-attribute]
                local_start = timezone.localtime(
                    self.start,
                    ZoneInfo(self.user.profile.timezone),  # ty: ignore[unresolved-attribute]
                )
                if self.recurrence_until < local_start.date():
                    errors["recurrence_until"] = (
                        "Дата завершення повторень не може бути раніше початку події."
                    )
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title


class Task(models.Model):
    class Priority(models.IntegerChoices):
        LOW = 1, "Низький"
        MEDIUM = 2, "Середній"
        HIGH = 3, "Високий"

    class Status(models.TextChoices):
        TODO = "todo", "До виконання"
        IN_PROGRESS = "in_progress", "У роботі"
        DONE = "done", "Виконано"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField("Назва", max_length=200)
    description = models.TextField("Опис", blank=True)
    deadline = models.DateTimeField("Дедлайн", null=True, blank=True)
    priority = models.SmallIntegerField(
        "Пріоритет",
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    estimated_minutes = models.PositiveSmallIntegerField(
        "Оцінка тривалості (хв)",
        validators=[MinValueValidator(5), MaxValueValidator(480)],
    )
    status = models.CharField(
        "Статус",
        max_length=11,
        choices=Status.choices,
        default=Status.TODO,
    )
    category = models.ForeignKey(
        Category,
        verbose_name="Категорія",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(
        "Виконано о", null=True, blank=True, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Завдання"
        verbose_name_plural = "Завдання"
        ordering = ("-created_at", "pk")
        indexes = [
            models.Index(
                fields=("user", "status", "deadline"),
                name="task_user_status_deadline_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    estimated_minutes__gte=5, estimated_minutes__lte=480
                ),
                name="task_duration_between_5_and_480",
            ),
            models.CheckConstraint(
                condition=models.Q(priority__in=(1, 2, 3)),
                name="task_valid_priority",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=("todo", "in_progress", "done")),
                name="task_valid_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status="done", completed_at__isnull=False)
                    | models.Q(
                        status__in=("todo", "in_progress"), completed_at__isnull=True
                    )
                ),
                name="task_completion_matches_status",
            ),
        ]

    @property
    def is_overdue(self):
        return (
            self.deadline is not None
            and self.status != self.Status.DONE
            and self.deadline < timezone.now()
        )

    def _sync_completed_at(self):
        if self.status == self.Status.DONE:
            self.completed_at = self.completed_at or timezone.now()
        else:
            self.completed_at = None  # ty: ignore[invalid-assignment]

    def clean(self):
        super().clean()
        self._sync_completed_at()
        if self.category_id and self.category.user_id != self.user_id:  # ty: ignore[unresolved-attribute]
            raise ValidationError({"category": "Виберіть власну категорію."})

    def save(self, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "status" in update_fields:
            self._sync_completed_at()
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"completed_at"}
        super().save(**kwargs)

    def __str__(self):
        return self.title


class Notification(models.Model):
    """In-app reminder for an event occurrence or a task deadline.

    One row per instance: the same series occurrence or deadline never
    produces a second reminder (unique constraints below).
    """

    class Kind(models.TextChoices):
        EVENT = "event", "Подія"
        DEADLINE = "deadline", "Дедлайн завдання"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    occurrence_start = models.DateTimeField(
        "Початок екземпляра", null=True, blank=True, editable=False
    )
    kind = models.CharField("Тип", max_length=8, choices=Kind.choices)
    message = models.CharField("Текст", max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField("Прочитано", null=True, blank=True)
    delivered_at = models.DateTimeField(
        "Показано тостом",
        null=True,
        blank=True,
        editable=False,
        help_text="Коли повідомлення було показано спливаючим тостом. Непрочитані, "
        "але недоставлені лише збільшують лічильник у меню.",
    )

    class Meta:
        ordering = ("-created_at", "pk")
        verbose_name = "Повідомлення"
        verbose_name_plural = "Повідомлення"
        constraints = [
            models.UniqueConstraint(
                fields=("event", "occurrence_start"),
                condition=models.Q(event__isnull=False),
                name="notification_unique_event_occurrence",
            ),
            models.UniqueConstraint(
                fields=("task", "kind"),
                condition=models.Q(task__isnull=False),
                name="notification_unique_task_deadline",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "read_at", "created_at"),
                name="notification_user_unread_idx",
            ),
            models.Index(
                fields=("user", "delivered_at", "created_at"),
                name="notification_user_undeliv_idx",
            ),
        ]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return self.message
