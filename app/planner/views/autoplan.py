from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from ..services.autoplan import (
    NO_SLOT_BEFORE_DEADLINE,
    NO_WORKING_HOURS,
    apply_plan,
    plan,
)
from ..services.recurrence import OccurrenceTimeError

REASON_LABELS = {
    NO_SLOT_BEFORE_DEADLINE: "немає вільного місця до дедлайну",
    NO_WORKING_HOURS: "немає робочих годин у горизонті планування",
}


class AutoplanView(LoginRequiredMixin, View):
    template_name = "planner/autoplan.html"
    http_method_names = ["get", "post", "head", "options"]

    def _preview(self, request):
        """Tasks in planning order, each with its proposed blocks."""
        try:
            result = plan(request.user)
        except OccurrenceTimeError as error:
            return {"planning_error": error.messages[0]}
        groups: list[tuple] = []
        index_by_task = {}
        for block in result.placed:
            if block.task.pk not in index_by_task:
                index_by_task[block.task.pk] = len(groups)
                groups.append((block.task, []))
            groups[index_by_task[block.task.pk]][1].append(block)
        return {
            "groups": [(task, blocks) for task, blocks in groups],
            "failed": [
                (failure.task, REASON_LABELS.get(failure.reason, failure.reason))
                for failure in result.failed
            ],
            "total_minutes": sum(
                int((block.end - block.start).total_seconds() // 60)
                for block in result.placed
            ),
        }

    def get(self, request):
        return render(request, self.template_name, self._preview(request))

    def post(self, request):
        """Recompute deterministically, then create all blocks at once."""
        try:
            result = plan(request.user)
        except OccurrenceTimeError as error:
            return render(
                request, self.template_name, {"planning_error": error.messages[0]}
            )
        events = apply_plan(request.user, result)
        if events:
            messages.success(
                request,
                f"Розміщено {len(events)} блоків у розкладі.",
            )
            return redirect(reverse("planner:calendar"))
        messages.warning(request, "Немає завдань для розміщення.")
        return redirect(reverse("planner:task_list"))
