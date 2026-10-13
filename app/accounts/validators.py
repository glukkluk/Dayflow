from zoneinfo import available_timezones

from django.core.exceptions import ValidationError


def validate_timezone(value):
    if value not in available_timezones():
        raise ValidationError("Виберіть чинний часовий пояс.", code="invalid_timezone")
