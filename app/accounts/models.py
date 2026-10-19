import uuid
from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

from .validators import validate_timezone


def avatar_path(instance, filename):
    return f"avatars/{instance.user_id}/{uuid.uuid4().hex}.webp"


class Profile(models.Model):
    class DateFormat(models.TextChoices):
        DMY_DOT = "dmy_dot", "ДД.ММ.РРРР"
        DMY_SLASH = "dmy_slash", "ДД/ММ/РРРР"
        MDY_SLASH = "mdy_slash", "ММ/ДД/РРРР"
        YMD_DASH = "ymd_dash", "РРРР-ММ-ДД"

    class TimeFormat(models.TextChoices):
        H24 = "24h", "24-годинний (14:30)"
        H12 = "12h", "12-годинний (2:30 PM)"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    timezone = models.CharField(
        "Часовий пояс",
        max_length=63,
        default="Europe/Kyiv",
        validators=[validate_timezone],
    )
    avatar = models.ImageField("Аватар", upload_to=avatar_path, blank=True)
    date_format = models.CharField(
        "Формат дати",
        max_length=9,
        choices=DateFormat.choices,
        default=DateFormat.DMY_DOT,
    )
    time_format = models.CharField(
        "Формат часу",
        max_length=3,
        choices=TimeFormat.choices,
        default=TimeFormat.H24,
    )
    work_start = models.TimeField("Початок робочого дня", default=time(9))
    work_end = models.TimeField("Кінець робочого дня", default=time(18))
    buffer_minutes = models.PositiveSmallIntegerField(
        "Буфер між подіями (хв)", default=10, validators=[MaxValueValidator(60)]
    )

    class Meta:
        verbose_name = "Профіль"
        verbose_name_plural = "Профілі"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(work_end__gt=models.F("work_start")),
                name="profile_work_end_after_start",
            ),
            models.CheckConstraint(
                condition=models.Q(buffer_minutes__gte=0, buffer_minutes__lte=60),
                name="profile_buffer_between_0_and_60",
            ),
        ]

    def clean(self):
        super().clean()
        if self.work_start and self.work_end and self.work_end <= self.work_start:
            raise ValidationError(
                {"work_end": "Кінець робочого дня має бути пізніше за початок."}
            )

    def __str__(self):
        return f"Профіль {self.user.get_username()}"  # ty: ignore[unresolved-attribute]
