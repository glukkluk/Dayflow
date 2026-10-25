"""Shared parsing and formatting for profile, event and task time inputs."""

import re
from datetime import time

from django import forms

from .widgets import TimeTextInput

_TIME_WITH_SEPARATOR = re.compile(r"^(\d{1,2})[:.\s](\d{1,2})$")
_TIME_DIGITS = re.compile(r"^\d{1,4}$")
_MERIDIEM = re.compile(r"\s*(AM|PM)$", re.IGNORECASE)


def time_error(hour12=False):
    return (
        "Укажіть час із AM або PM, наприклад 2:30 PM."
        if hour12
        else "Вкажіть час у форматі ГГ:ХХ, наприклад 13 або 13:30."
    )


def parse_time_text(text, hour12=False):
    """Parse shorthand time; 12-hour input requires an explicit AM/PM suffix.

    Mirrors ``planner/time_input.js``. Empty input yields None; invalid input
    raises ValueError. 12 AM is midnight and 12 PM is noon.
    """
    text = (text or "").strip()
    if not text:
        return None
    meridiem = None
    if hour12:
        match = _MERIDIEM.search(text)
        if not match:
            raise ValueError(text)
        meridiem = match[1].upper()
        text = text[:match.start()].strip()
    if match := _TIME_WITH_SEPARATOR.fullmatch(text):
        hour, minute = int(match[1]), int(match[2])
    elif _TIME_DIGITS.fullmatch(text):
        if len(text) <= 2:
            hour, minute = int(text), 0
        else:
            hour, minute = int(text[:-2]), int(text[-2:])
    else:
        raise ValueError(text)
    if minute > 59 or hour > (12 if hour12 else 23) or (hour12 and hour < 1):
        raise ValueError(text)
    if hour12:
        hour = hour % 12 + (12 if meridiem == "PM" else 0)
    return time(hour, minute)


class ProfileTimeField(forms.TimeField):
    widget = TimeTextInput

    def set_time_format(self, key):
        self.widget.set_time_format(key)

    def to_python(self, value):
        if not isinstance(value, str):
            return super().to_python(value)
        hour12 = self.widget.hour12
        try:
            return parse_time_text(value, hour12)
        except ValueError:
            raise forms.ValidationError(time_error(hour12), code="invalid") from None
