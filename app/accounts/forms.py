from datetime import UTC, datetime
from io import BytesIO
from zoneinfo import ZoneInfo, available_timezones

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

from .models import Profile


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Електронна пошта", required=True)

    class Meta(UserCreationForm.Meta):  # ty: ignore[invalid-attribute-override]
        model = get_user_model()
        fields = ("username", "email", "password1", "password2")


def _timezone_choices():
    """Timezones grouped by region, labelled with their current UTC offset."""
    now = datetime.now(UTC)
    groups = {}
    for name in sorted(available_timezones()):
        region = name.split("/", 1)[0] if "/" in name else "Інше"
        offset = now.astimezone(ZoneInfo(name)).utcoffset()
        minutes = int(offset.total_seconds() // 60)  # ty: ignore[unresolved-attribute]
        sign = "+" if minutes >= 0 else "-"
        label = f"{name} (UTC{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d})"
        groups.setdefault(region, []).append((name, label))
    return [(region, choices) for region, choices in groups.items()]


class ProfileForm(forms.ModelForm):
    """General settings: timezone, date/time display, work hours, buffer."""

    timezone = forms.ChoiceField(
        label="Часовий пояс",
        help_text=(
            "Часовий пояс, у якому вводяться й показуються дата та час подій. "
            "Приклад: Europe/Kyiv — подія о 14:00 відображається як 14:00 за київським часом."
        ),
    )
    date_format = forms.ChoiceField(
        label="Формат дати",
        choices=Profile.DateFormat.choices,
        help_text=(
            "Як показувати дати в списках, на дашборді й у сповіщеннях. "
            "Приклад: ДД.ММ.РРРР → 31.12.2026, РРРР-ММ-ДД → 2026-12-31."
        ),
    )
    time_format = forms.ChoiceField(
        label="Формат часу",
        choices=Profile.TimeFormat.choices,
        help_text=(
            "24-годинний чи 12-годинний (AM/PM) вигляд часу. "
            "Приклад: 14:30 у 24-годинному форматі — це 2:30 PM у 12-годинному. "
            "Поля введення часу у формі події завжди 24-годинні."
        ),
    )
    work_start = forms.TimeField(
        label="Початок робочого дня",
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        help_text=(
            "З цього часу автопланування починає ставити завдання, а календар "
            "підсвічує робочі години. Приклад: 09:00."
        ),
    )
    work_end = forms.TimeField(
        label="Кінець робочого дня",
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        help_text=(
            "Після цього часу автопланування не планує завдання. "
            "Має бути пізніше за початок. Приклад: 18:00."
        ),
    )
    buffer_minutes = forms.IntegerField(
        label="Буферні хвилини",
        min_value=0,
        max_value=60,
        help_text=(
            "Пауза між подіями, яку автопланування залишає між завданнями (0–60 хв). "
            "Приклад: за 10 хв два завдання підряд матимуть 10 хв перерви між собою."
        ),
    )

    class Meta:
        model = Profile
        fields = (
            "timezone",
            "date_format",
            "time_format",
            "work_start",
            "work_end",
            "buffer_minutes",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["timezone"].choices = _timezone_choices()


class UsernameForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Ім'я користувача"
        self.fields["username"].help_text = (
            "Логін для входу, до 150 символів: літери, цифри та @/./+/-/_. "
            "Приклад: olena_k. Має бути унікальним."
        )


AVATAR_SIZE = 256
AVATAR_MAX_BYTES = 5 * 1024 * 1024


class AvatarForm(forms.Form):
    avatar = forms.ImageField(
        label="Новий аватар",
        help_text=(
            "Зображення JPG, PNG, WebP або GIF до 5 МБ. Його буде обрізано до квадрата "
            "256×256. Приклад: портретне фото обличчя."
        ),
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
    )

    def clean_avatar(self):
        upload = self.cleaned_data["avatar"]
        if upload.size > AVATAR_MAX_BYTES:
            raise forms.ValidationError("Файл завеликий: максимум 5 МБ.")
        return upload

    def save(self, profile):
        upload = self.cleaned_data["avatar"]
        upload.seek(0)
        with Image.open(upload) as source:
            image = ImageOps.exif_transpose(source)
            image = ImageOps.fit(image.convert("RGBA"), (AVATAR_SIZE, AVATAR_SIZE))
        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=85)
        old = profile.avatar.name
        profile.avatar.save("avatar.webp", ContentFile(buffer.getvalue()), save=True)
        if old and old != profile.avatar.name:
            profile.avatar.storage.delete(old)


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Поточний пароль",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        help_text="Введіть пароль, щоб підтвердити, що це ви.",
    )
    confirm = forms.BooleanField(
        label="Я розумію, що акаунт і всі мої дані буде видалено назавжди"
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Невірний пароль.")
        return password
