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
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField("Назва", max_length=200)
    description = models.TextField("Опис", blank=True)
    start = models.DateTimeField("Початок")
    end = models.DateTimeField("Кінець")
    all_day = models.BooleanField("Весь день", default=False)
    category = models.ForeignKey(
        Category,
        verbose_name="Категорія",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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
            )
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
        if self.category_id and self.category.user_id != self.user_id:  # ty: ignore[unresolved-attribute]
            errors["category"] = "Виберіть власну категорію."
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
