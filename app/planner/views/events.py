from datetime import datetime, time, timedelta
from itertools import groupby
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from ..forms import EventForm
from ..models import Event
from ..services.conflicts import check_event


EVENT_PERIODS = (
    ("past", "Раніше"),
    ("yesterday", "Вчора"),
    ("today", "Сьогодні"),
    ("tomorrow", "Завтра"),
    ("future", "Пізніше"),
)


def event_period(start, today, tz):
    day = timezone.localtime(start, tz).date()
    delta = (day - today).days
    if delta < -1:
        return "past"
    if delta == -1:
        return "yesterday"
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    return "future"


def return_destination(request, sources, default):
    source = request.GET.get("from", "")
    key, label = sources.get(source, (default, "Назад до списку"))
    return reverse(key), label


class EventOwnerMixin(LoginRequiredMixin):
    model = Event

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user).select_related("category")  # ty: ignore[unresolved-attribute]


class EventFormMixin(SuccessMessageMixin):
    form_class = EventForm
    template_name = "planner/form.html"
    success_message = "Подію збережено."

    def form_valid(self, form):
        try:
            result = check_event(form.instance)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)  # ty: ignore[unresolved-attribute]
        except (ValueError, OverflowError):
            form.add_error(None, "Неможливо перевірити повторення для цього діапазону дат.")
            return self.form_invalid(form)  # ty: ignore[unresolved-attribute]
        if result.conflicts and self.request.POST.get("force") != "true":  # ty: ignore[unresolved-attribute]
            return self.render_to_response(  # ty: ignore[unresolved-attribute]
                self.get_context_data(form=form, conflict_check=result)
            )
        return super().form_valid(form)

    def get_success_url(self):
        url = reverse("planner:event_detail", kwargs={"pk": self.object.pk})  # ty: ignore[unresolved-attribute]
        source = self.request.GET.get("from")
        if source in ("dashboard", "events", "calendar"):
            return f"{url}?{urlencode({'from': source})}"
        return url

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  # ty: ignore[unresolved-attribute]
        context["cancel_url"] = "planner:event_list"
        context["back_url"], context["back_label"] = return_destination(
            self.request,
            {
                "dashboard": ("planner:dashboard", "Назад на дашборд"),
                "events": ("planner:event_list", "Назад до списку"),
                "calendar": ("planner:calendar", "Назад до календаря"),
            },
            "planner:event_list",
        )
        context["note"] = (
            f"Дата й час у часовому поясі {self.request.user.profile.timezone}."  # ty: ignore[unresolved-attribute]
            " Редагування повторюваної події змінює всю серію."
            " Для серії без кінцевої дати конфлікти перевіряються на 365 днів уперед"
            " від початку або поточного моменту для старих серій."
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

        self.today = timezone.localdate()
        self.tz = timezone.get_current_timezone()
        start_yesterday = timezone.make_aware(
            datetime.combine(self.today - timedelta(days=1), time.min), self.tz
        )
        start_today = timezone.make_aware(datetime.combine(self.today, time.min), self.tz)
        start_tomorrow = timezone.make_aware(
            datetime.combine(self.today + timedelta(days=1), time.min), self.tz
        )
        start_after_tomorrow = timezone.make_aware(
            datetime.combine(self.today + timedelta(days=2), time.min), self.tz
        )
        self.period_filters = {
            "past": Q(start__lt=start_yesterday),
            "yesterday": Q(start__gte=start_yesterday, start__lt=start_today),
            "today": Q(start__gte=start_today, start__lt=start_tomorrow),
            "tomorrow": Q(start__gte=start_tomorrow, start__lt=start_after_tomorrow),
            "future": Q(start__gte=start_after_tomorrow),
        }
        self.period_counts = {
            key: events.filter(rule).count() for key, rule in self.period_filters.items()
        }
        requested = self.request.GET.get("period", "all")
        self.period = requested if requested in self.period_filters else "all"
        if self.period != "all":
            events = events.filter(self.period_filters[self.period])
        return events.order_by("start", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        context["period"] = self.period
        context["total_count"] = sum(self.period_counts.values())
        context["period_tabs"] = [
            {"key": key, "label": label, "count": self.period_counts[key]}
            for key, label in EVENT_PERIODS
        ]
        names = dict(EVENT_PERIODS)
        context["period_groups"] = [
            {"key": key, "label": names[key], "events": list(events)}
            for key, events in groupby(
                context["page_obj"],
                key=lambda event: event_period(event.start, self.today, self.tz),
            )
        ]
        return context


class EventDetailView(EventOwnerMixin, DetailView):
    template_name = "planner/event_detail.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_url"], context["back_label"] = return_destination(
            self.request,
            {
                "dashboard": ("planner:dashboard", "Назад на дашборд"),
                "events": ("planner:event_list", "Назад до списку"),
                "calendar": ("planner:calendar", "Назад до календаря"),
            },
            "planner:event_list",
        )
        origin = self.request.GET.get("from")
        context["event_origin"] = (
            origin if origin in ("dashboard", "events", "calendar") else "events"
        )
        return context


class EventCreateView(EventOwnerMixin, EventFormMixin, CreateView):
    extra_context = {"title": "Нова подія"}

    def get_initial(self):
        initial = super().get_initial()
        for field in ("start", "end"):
            try:
                value = parse_datetime(self.request.GET.get(field, ""))
            except ValueError:
                value = None
            if value:
                initial[field] = value
        initial["all_day"] = self.request.GET.get("all_day") == "true"
        return initial

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
