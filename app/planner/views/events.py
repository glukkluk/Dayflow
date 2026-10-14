from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from ..forms import EventForm
from ..models import Event


class EventOwnerMixin(LoginRequiredMixin):
    model = Event

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user).select_related("category")  # ty: ignore[unresolved-attribute]

class EventFormMixin(SuccessMessageMixin):
    form_class = EventForm
    template_name = "planner/form.html"
    success_message = "Подію збережено."

    def get_success_url(self):
        return reverse("planner:event_detail", kwargs={"pk": self.object.pk})  # ty: ignore[unresolved-attribute]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  # ty: ignore[unresolved-attribute]
        context["cancel_url"] = "planner:event_list"
        context["note"] = (
            f"Дата й час у часовому поясі {self.request.user.profile.timezone}."  # ty: ignore[unresolved-attribute]
            " Редагування повторюваної події змінює всю серію."
        )
        return context

class EventListView(EventOwnerMixin, ListView):
    template_name = "planner/event_list.html"
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get("q", "").strip()
        events = super().get_queryset()
        if query:
            events = events.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        return events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        return context


class EventDetailView(EventOwnerMixin, DetailView):
    template_name = "planner/event_detail.html"
    context_object_name = "event"


class EventCreateView(EventOwnerMixin, EventFormMixin, CreateView):
    extra_context = {"title": "Нова подія"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Event(user=self.request.user)
        return kwargs


class EventEditView(EventOwnerMixin, EventFormMixin, UpdateView):
    extra_context = {"title": "Редагувати подію"}


class EventDeleteView(EventOwnerMixin, DeleteView):
    template_name = "planner/confirm_delete.html"
    success_url = reverse_lazy("planner:event_list")
    extra_context = {
        "title": "Видалити подію",
        "cancel_url": "planner:event_list",
        "note": "Для повторюваної події буде видалено всю серію.",
    }

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Подію видалено.")
        return response
