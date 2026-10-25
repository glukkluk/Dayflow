from datetime import date, datetime, time, timedelta

from accounts.time_inputs import parse_time_text, time_error
from accounts.widgets import ProfileDateInput, TimeTextInput, configure_date_field
from django import forms
from django.forms.utils import from_current_timezone
from django.utils import timezone

from .models import Category, Event, Task


class DateAndTimeWidget(forms.MultiWidget):
    """A date picker plus a free-text time input (hidden for all-day events)."""

    class Media:
        js = ("planner/time_input.js",)

    def __init__(self, attrs=None):
        widgets = (
            ProfileDateInput(),
            TimeTextInput(),
        )
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if isinstance(value, datetime):
            if timezone.is_aware(value):
                value = timezone.localtime(value)
            return [value.date(), value.time()]
        if isinstance(value, date):
            return [value, None]
        return [None, None]

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["subwidgets"][1]["attrs"].pop("required", None)
        return context


class DateAndTimeField(forms.MultiValueField):
    """Yields ``(date, time | None)``; the form combines it with ``all_day``."""

    widget = DateAndTimeWidget

    def __init__(self, **kwargs):
        fields = (forms.DateField(), forms.CharField(required=False))
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def set_profile(self, profile):
        day = self.fields[0]
        day.widget = self.widget.widgets[0]  # ty: ignore[unresolved-attribute]
        configure_date_field(day, profile)
        self.widget.widgets[1].set_time_format(getattr(profile, "time_format", "24h"))  # ty: ignore[unresolved-attribute]

    @property
    def time_error(self):
        return time_error(self.widget.widgets[1].hour12)  # ty: ignore[unresolved-attribute]

    def compress(self, data_list):
        if not data_list:
            return None
        day, text = data_list
        try:
            return day, parse_time_text(text, self.widget.widgets[1].hour12)  # ty: ignore[unresolved-attribute]
        except ValueError:
            raise forms.ValidationError(
                self.time_error,
                code="invalid_time",
            ) from None


def _local(value):
    return timezone.localtime(value) if timezone.is_aware(value) else value


def _combine(day, clock):
    """Local date + time -> aware datetime; DST gaps/overlaps raise ValidationError."""
    return from_current_timezone(datetime.combine(day, clock))


# Reminder lead times (minutes) offered for timed and all-day events.
TIMED_REMINDERS = (5, 15, 30, 60, 1440)
ALL_DAY_REMINDERS = (1440, 4320, 10080)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "color")
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}

    def clean_name(self):
        name = self.cleaned_data["name"]
        duplicates = Category.objects.filter(  # ty: ignore[unresolved-attribute]
            user=self.instance.user, name=name
        )
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("Категорія з такою назвою вже існує.")
        return name


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = (
            "title",
            "description",
            "start",
            "end",
            "category",
            "all_day",
            "recurrence",
            "recurrence_until",
            "reminder_minutes",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "recurrence_until": ProfileDateInput(),
        }

    field_order = (
        "title",
        "description",
        "all_day",
        "start",
        "end",
        "category",
        "recurrence",
        "recurrence_until",
        "reminder_minutes",
    )

    start = DateAndTimeField(label="Початок")
    end = DateAndTimeField(
        label="Кінець",
        help_text="Для події на весь день — остання дата включно.",
    )

    class Media:
        js = ("planner/time_input.js", "planner/event_form.js")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = self.instance.user.profile if self.instance.user_id else None
        for name in ("start", "end"):
            self.fields[name].set_profile(profile)
        configure_date_field(self.fields["recurrence_until"], profile)
        self.fields["category"].queryset = Category.objects.filter(  # ty: ignore[unresolved-attribute]
            user_id=self.instance.user_id
        )
        self.fields["category"].empty_label = "Без категорії"
        self.fields["reminder_minutes"].choices = [
            ("", "Без нагадування"),
            *self.fields["reminder_minutes"].choices[1:],
        ]
        all_day_field = self.fields["all_day"]
        all_day_field.widget.attrs.update(
            {
                "data-timezone": timezone.get_current_timezone_name(),
                "data-reminders-timed": ",".join(map(str, TIMED_REMINDERS)),
                "data-reminders-all-day": ",".join(map(str, ALL_DAY_REMINDERS)),
            }
        )
        if self.initial.get("all_day"):
            # Show dates only; the stored end is exclusive, the form's is inclusive.
            start, end = self.initial.get("start"), self.initial.get("end")
            if isinstance(start, datetime):
                self.initial["start"] = _local(start).date()
            if isinstance(end, datetime):
                end = _local(end)
                last_day = end.date()
                if end.time() == time.min:
                    last_day -= timedelta(days=1)
                self.initial["end"] = last_day

    def clean(self):
        cleaned = super().clean()
        reminder = cleaned.get("reminder_minutes")
        allowed = ALL_DAY_REMINDERS if cleaned.get("all_day") else TIMED_REMINDERS
        if reminder is not None and reminder not in allowed:
            self.add_error(
                "reminder_minutes",
                "Для події на весь день доступні лише нагадування за 1 день, 3 дні або тиждень."
                if cleaned.get("all_day")
                else "Таке нагадування доступне лише для події на весь день.",
            )
        start, end = cleaned.get("start"), cleaned.get("end")
        if start is None or end is None:
            cleaned.pop("start", None)
            cleaned.pop("end", None)
            return cleaned
        try:
            combined = self._combine_start_end(start, end, cleaned.get("all_day"))
        except forms.ValidationError as error:
            combined = None
            self.add_error(None, error)
        except OverflowError:
            combined = None
            self.add_error(None, "Дата виходить за межі допустимого діапазону.")
        if combined is None:
            # Never leave the raw (date, time) tuples where construct_instance sees them.
            cleaned.pop("start", None)
            cleaned.pop("end", None)
        else:
            cleaned["start"], cleaned["end"] = combined
        return cleaned

    def _combine_start_end(self, start, end, all_day):
        if all_day:
            # Times are ignored; the stored end is exclusive (midnight after the last day).
            return (
                _combine(start[0], time.min),
                _combine(end[0] + timedelta(days=1), time.min),
            )
        missing = False
        for name, (_, clock) in (("start", start), ("end", end)):
            if clock is None:
                self.add_error(name, self.fields[name].time_error)
                missing = True
        if missing:
            return None
        return _combine(*start), _combine(*end)


class TaskForm(forms.ModelForm):
    deadline = DateAndTimeField(label="Дедлайн", required=False)

    no_deadline = forms.BooleanField(
        label="Вільне завдання",
        required=False,
        help_text="Можна взяти у вільний час. Укажіть орієнтовну тривалість нижче.",
    )

    field_order = (
        "title",
        "description",
        "no_deadline",
        "deadline",
        "estimated_minutes",
        "priority",
        "status",
        "category",
    )

    class Media:
        js = ("planner/time_input.js", "planner/task_form.js")

    class Meta:
        model = Task
        fields = (
            "title",
            "description",
            "deadline",
            "priority",
            "estimated_minutes",
            "status",
            "category",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "estimated_minutes": forms.NumberInput(attrs={"min": 5, "max": 480}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = self.instance.user.profile if self.instance.user_id else None
        self.fields["deadline"].set_profile(profile)
        self.fields["category"].queryset = Category.objects.filter(  # ty: ignore[unresolved-attribute]
            user_id=self.instance.user_id,
        )
        self.fields["category"].empty_label = "Без категорії"
        if self.instance.pk:
            self.initial["no_deadline"] = self.instance.deadline is None
        else:
            self.initial["no_deadline"] = False
        self._already_started_free = bool(
            self.instance.pk
            and self.instance.deadline is None
            and self.instance.status == Task.Status.IN_PROGRESS
        )
        self.fields["status"].widget.attrs["data-started-free"] = (
            "true" if self._already_started_free else "false"
        )
        self.fields["status"].help_text = (
            "Вільне завдання береться в роботу через кнопку «Взяти вільне завдання» "
            "на дашборді — з перевіркою конфліктів і розміщенням у розкладі."
        )
        self.fields[
            "deadline"
        ].help_text = (
            "Укажіть дату й час. Для завдання без дедлайну увімкніть «Вільне завдання»."
        )
        self.fields["estimated_minutes"].label = "Орієнтовна тривалість (хв)"
        self.fields["estimated_minutes"].help_text = (
            "Від 5 до 480 хвилин. Обов'язково для вільного завдання; "
            "для завдання з дедлайном можна не вказувати."
        )
        if self.is_bound and self["no_deadline"].value():
            self.fields["deadline"].disabled = True
            self.initial["deadline"] = None

        is_free = bool(self["no_deadline"].value())
        self.fields["deadline"].required = not is_free
        self.fields["estimated_minutes"].required = is_free
        self.fields["estimated_minutes"].error_messages["required"] = (
            "Для вільного завдання вкажіть орієнтовну тривалість."
        )

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        if deadline is None:
            return None
        day, clock = deadline
        if clock is None:
            raise forms.ValidationError(self.fields["deadline"].time_error)
        return _combine(day, clock)

    def clean(self):
        cleaned = super().clean()
        if (
            "deadline" in cleaned
            and cleaned["deadline"] is None
            and cleaned.get("status") == Task.Status.IN_PROGRESS
            and not self._already_started_free
        ):
            self.add_error(
                "status",
                "Вільне завдання не можна вручну перевести у статус «У роботі». "
                "Збережіть його зі статусом «До виконання» та візьміть через дашборд.",
            )
        return cleaned


class FreeTimeForm(forms.Form):
    amount = forms.IntegerField(
        label="Скільки маєте часу?",
        min_value=1,
        initial=30,
        widget=forms.NumberInput(attrs={"step": 1, "max": 59}),
    )
    unit = forms.ChoiceField(
        label="Одиниця часу",
        choices=(("minutes", "Хвилини"), ("hours", "Години")),
        initial="minutes",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount"].widget.attrs["max"] = (
            24 if self["unit"].value() == "hours" else 59
        )

    def clean(self):
        cleaned = super().clean()
        amount, unit = cleaned.get("amount"), cleaned.get("unit")
        if amount is not None and unit:
            maximum = 24 if unit == "hours" else 59
            if amount > maximum:
                self.add_error(
                    "amount",
                    f"Укажіть не більше {maximum} {'годин' if unit == 'hours' else 'хвилин'}.",
                )
            else:
                cleaned["minutes"] = amount * (60 if unit == "hours" else 1)
        return cleaned


class TaskFilterForm(forms.Form):
    q = forms.CharField(
        label="Пошук за назвою або описом",
        required=False,
        widget=forms.TextInput(
            attrs={"type": "search", "placeholder": "Назва або опис завдання…"}
        ),
    )
    status = forms.ChoiceField(
        label="Статус",
        choices=[("", "Усі статуси"), *Task.Status.choices, ("active", "Невиконані")],
        required=False,
    )
    priority = forms.ChoiceField(
        label="Пріоритет",
        choices=[("", "Усі пріоритети"), *Task.Priority.choices],
        required=False,
    )
    category = forms.ModelChoiceField(
        label="Категорія",
        queryset=Category.objects.none(),  # ty: ignore[unresolved-attribute]
        empty_label="Усі категорії",
        required=False,
    )
    not_overdue = forms.BooleanField(label="Не прострочені", required=False)
    overdue = forms.BooleanField(label="Лише прострочені", required=False)
    free = forms.BooleanField(label="Вільні завдання", required=False)
    sort = forms.ChoiceField(
        label="Сортування",
        required=False,
        choices=[
            ("deadline", "За дедлайном"),
            ("priority", "За пріоритетом"),
            ("created", "Спочатку нові"),
        ],
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user)  # ty: ignore[unresolved-attribute]
