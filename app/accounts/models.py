from datetime import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

from .validators import validate_timezone


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    timezone = models.CharField(
        "Часовий пояс",
        max_length=63,
        default="Europe/Kyiv",
        validators=[validate_timezone],
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
        return f"Профіль {self.user.get_username()}"
