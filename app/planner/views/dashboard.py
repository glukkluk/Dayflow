from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.views.generic import TemplateView

from ..services.dashboard import summarize


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "planner/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context.update(summarize(self.request.user))
        except ValidationError as error:
            context["dashboard_error"] = " ".join(error.messages)
        return context
