from django import forms

from .models import Category, Event, Task


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
        fields = ("title", "description", "start", "end", "category", "all_day")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "start": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "end": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(  # ty: ignore[unresolved-attribute]
            user_id=self.instance.user_id
        )


class TaskForm(forms.ModelForm):
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
            "deadline": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
            "estimated_minutes": forms.NumberInput(attrs={"min": 5, "max": 480}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(  # ty: ignore[unresolved-attribute]
            user_id=self.instance.user_id,
        )


class TaskFilterForm(forms.Form):
    q = forms.CharField(label="Пошук за назвою або описом", required=False)
    status = forms.ChoiceField(
        label="Статус",
        choices=[("", "Усі статуси"), *Task.Status.choices],
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
    overdue = forms.BooleanField(label="Лише прострочені", required=False)
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
