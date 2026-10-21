from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.cache import patch_vary_headers
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from ..forms import TaskFilterForm, TaskForm
from ..models import Task


class TaskOwnerMixin(LoginRequiredMixin):
    model = Task

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user).select_related("category")  # ty: ignore[unresolved-attribute]


class TaskFormMixin(SuccessMessageMixin):
    form_class = TaskForm
    template_name = "planner/form.html"
    success_url = reverse_lazy("planner:task_list")
    success_message = "Завдання збережено."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  # ty: ignore[unresolved-attribute]
        context["cancel_url"] = "planner:task_list"
        context["back_url"], context["back_label"] = (
            (reverse("planner:dashboard"), "Назад на дашборд")
            if self.request.GET.get("from") == "dashboard"  # ty: ignore[unresolved-attribute]
            else (reverse("planner:task_list"), "Назад до списку")
        )
        context["note"] = (
            f"Дедлайн у часовому поясі {self.request.user.profile.timezone}."  # ty: ignore[unresolved-attribute]
        )
        return context


class TaskListView(TaskOwnerMixin, ListView):
    template_name = "planner/task_list.html"
    paginate_by = 20

    def get_queryset(self):
        tasks = super().get_queryset().prefetch_related("scheduled_events")
        self.filter_form = TaskFilterForm(self.request.GET, user=self.request.user)
        if not self.filter_form.is_valid():
            return tasks.none()
        filters = self.filter_form.cleaned_data
        if filters["q"]:
            tasks = tasks.filter(
                Q(title__icontains=filters["q"])
                | Q(description__icontains=filters["q"])
            )
        for field in ("status", "priority", "category"):
            if filters[field]:
                tasks = tasks.filter(**{field: filters[field]})
        if filters["overdue"]:
            tasks = tasks.filter(deadline__lt=timezone.now()).exclude(
                status=Task.Status.DONE
            )
        ordering = {
            "deadline": (F("deadline").asc(nulls_last=True), "pk"),
            "priority": ("-priority", F("deadline").asc(nulls_last=True), "pk"),
            "created": ("-created_at", "pk"),
        }
        return tasks.order_by(*ordering[filters["sort"] or "deadline"])

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(queryset, page_size)
        page = paginator.get_page(self.request.GET.get("page"))
        return paginator, page, page.object_list, page.has_other_pages()

    def get_template_names(self):
        if (
            self.request.headers.get("HX-Request") == "true"
            and self.request.headers.get("HX-History-Restore-Request") != "true"
        ):
            return ["planner/partials/task_results.html"]
        return super().get_template_names()

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        patch_vary_headers(response, ["HX-Request", "HX-History-Restore-Request"])
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["query_string"] = self.request.GET.urlencode()
        return context


class TaskCreateView(TaskOwnerMixin, TaskFormMixin, CreateView):
    extra_context = {"title": "Нове завдання"}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Task(user=self.request.user)
        return kwargs


class TaskEditView(TaskOwnerMixin, TaskFormMixin, UpdateView):
    extra_context = {"title": "Редагувати завдання"}


class TaskDeleteView(TaskOwnerMixin, DeleteView):
    template_name = "planner/confirm_delete.html"
    success_url = reverse_lazy("planner:task_list")
    http_method_names = ["get", "post", "head", "options"]
    extra_context = {"title": "Видалити завдання", "cancel_url": "planner:task_list"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.scheduled_events.exists():
            context["note"] = (
                "Разом із завданням буде видалено розміщені для нього події."
            )
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Завдання видалено.")
        return response


class TaskToggleView(TaskOwnerMixin, SingleObjectMixin, View):
    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        task = self.get_object()
        task.status = (
            Task.Status.TODO if task.status == Task.Status.DONE else Task.Status.DONE
        )
        task.save(update_fields=["status"])

        if request.headers.get("HX-Request") == "true":
            return HttpResponse(status=204, headers={"HX-Trigger": "tasksChanged"})
        messages.success(request, "Статус завдання змінено.")

        url = reverse("planner:task_list")
        query = request.GET.urlencode()
        return redirect(f"{url}?{query}" if query else url)
