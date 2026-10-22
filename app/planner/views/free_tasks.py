from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.cache import patch_vary_headers
from django.views import View
from django.views.generic import TemplateView

from ..forms import FreeTimeForm
from ..models import Task
from ..services.free_tasks import suggestions, take_task


class FreeTaskSuggestionsView(LoginRequiredMixin, TemplateView):
    template_name = "planner/free_tasks.html"

    def get_template_names(self):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return ["planner/partials/free_task_results.html"]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = FreeTimeForm(self.request.GET)
        context["free_time_form"] = form
        if form.is_valid():
            context["free_minutes"] = form.cleaned_data["minutes"]
            context["free_tasks"] = suggestions(
                self.request.user, context["free_minutes"]
            )
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        patch_vary_headers(response, ["X-Requested-With"])
        return response


class FreeTaskTakeView(LoginRequiredMixin, View):
    http_method_names = ["post", "options"]

    def post(self, request, pk):
        get_object_or_404(Task, user=request.user, pk=pk)
        form = FreeTimeForm(request.POST)
        if not form.is_valid():
            messages.error(
                request,
                "Укажіть вільний час: від 1 до 59 хвилин або від 1 до 24 годин.",
            )
            return redirect("planner:dashboard")
        try:
            result = take_task(
                request.user, pk, form.cleaned_data["minutes"],
                force=request.POST.get("force") == "true",
            )
        except Task.DoesNotExist:  # ty: ignore[unresolved-attribute]
            raise Http404 from None
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        except (ValueError, OverflowError):
            messages.error(request, "Неможливо перевірити повторення для цього діапазону дат.")
        else:
            if result.event.pk is None:
                return render(request, "planner/free_task_conflicts.html", {
                    "task": result.task,
                    "conflict_check": result.conflict_check,
                    "free_time_form": form,
                })
            messages.success(
                request,
                f"Завдання «{result.task.title}» взято в роботу й додано до розкладу.",
            )
        return redirect("planner:dashboard")
