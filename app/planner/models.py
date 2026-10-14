from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


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
