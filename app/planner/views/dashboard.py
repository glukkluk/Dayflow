from django.core.exceptions import ValidationError
from django.views.generic import TemplateView

from ..services.dashboard import summarize


class DashboardView(TemplateView):
    """Show a public welcome page, or the private dashboard after sign-in."""

    def get_template_names(self):
        if not self.request.user.is_authenticated:
            return ["planner/landing.html"]
        return ["planner/dashboard.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.user.is_authenticated:
            return context
        try:
            context.update(summarize(self.request.user))
        except ValidationError as error:
            context["dashboard_error"] = " ".join(error.messages)
        return context
