from zoneinfo import available_timezones

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Електронна пошта", required=True)

    class Meta(UserCreationForm.Meta):  # ty: ignore[invalid-attribute-override]
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")


class ProfileForm(forms.ModelForm):
    timezone = forms.ChoiceField(
        label="Часовий пояс",
        choices=[(name, name) for name in sorted(available_timezones())],
    )
    work_start = forms.TimeField(
        label="Початок робочого дня",
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )
    work_end = forms.TimeField(
        label="Кінець робочого дня",
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )
    buffer_minutes = forms.IntegerField(
        label="Буферні хвилини", min_value=0, max_value=60
    )

    class Meta:
        model = Profile
        fields = ("timezone", "work_start", "work_end", "buffer_minutes")
