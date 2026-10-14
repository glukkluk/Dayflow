from django import forms

from .models import Category, Event


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "color")
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}

    def clean_name(self):
        name = self.cleaned_data["name"]
        duplicates = Category.objects.filter(user=self.instance.user, name=name)  # ty: ignore[unresolved-attribute]
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
