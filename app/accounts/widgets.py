from datetime import datetime, time

from django import forms

from .models import Profile


DATE_INPUT_FORMATS = {
    Profile.DateFormat.DMY_DOT: ("%d.%m.%Y", "ДД.ММ.РРРР"),
    Profile.DateFormat.DMY_SLASH: ("%d/%m/%Y", "ДД/ММ/РРРР"),
    Profile.DateFormat.MDY_SLASH: ("%m/%d/%Y", "ММ/ДД/РРРР"),
    Profile.DateFormat.YMD_DASH: ("%Y-%m-%d", "РРРР-ММ-ДД"),
}


class ProfileDateInput(forms.DateInput):
    template_name = "accounts/widgets/date_input.html"

    class Media:
        js = ("accounts/date_input.js",)
        css = {"all": ("accounts/date_input.css",)}

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs)
        self.set_date_format(Profile.DateFormat.DMY_DOT)

    def set_date_format(self, key):
        if key not in DATE_INPUT_FORMATS:
            key = Profile.DateFormat.DMY_DOT
        self.format, placeholder = DATE_INPUT_FORMATS[key]
        self.attrs.update(
            {
                "data-date-format": key,
                "placeholder": placeholder,
                "autocomplete": "off",
                "maxlength": 10,
            }
        )


def configure_date_field(field, profile):
    field.widget.set_date_format(getattr(profile, "date_format", Profile.DateFormat.DMY_DOT))
    # Keep ISO input compatible with calendar links and existing clients.
    field.input_formats = (field.widget.format, "%Y-%m-%d")
    field.error_messages["invalid"] = (
        f"Укажіть дійсну дату у форматі {field.widget.attrs['placeholder']}."
    )


class TimeTextInput(forms.TimeInput):
    class Media:
        js = ("planner/time_input.js",)

    def __init__(self, attrs=None):
        super().__init__(
            format="%H:%M",
            attrs={
                "data-time-input": "",
                "placeholder": "ГГ:ХХ",
                "maxlength": 5,
                "autocomplete": "off",
                **(attrs or {}),
            },
        )
        self.set_time_format(Profile.TimeFormat.H24)

    def set_time_format(self, key):
        self.hour12 = key == Profile.TimeFormat.H12
        self.attrs.update(
            {
                "data-time-format": "12h" if self.hour12 else "24h",
                "placeholder": "Г:ХХ AM/PM" if self.hour12 else "ГГ:ХХ",
                "maxlength": 8 if self.hour12 else 5,
                "size": 10 if self.hour12 else 6,
            }
        )

    def format_value(self, value):
        if isinstance(value, (datetime, time)) and self.hour12:
            suffix = "AM" if value.hour < 12 else "PM"
            return f"{value.hour % 12 or 12}:{value.minute:02d} {suffix}"
        return super().format_value(value)
