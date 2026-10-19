from accounts.formats import get_formats
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import TemplateView


class CalendarView(LoginRequiredMixin, TemplateView):
    template_name = "planner/calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.profile
        formats = get_formats(profile)
        context["calendar_config"] = {
            "timezone": profile.timezone,
            "workStart": profile.work_start.strftime("%H:%M"),
            "workEnd": profile.work_end.strftime("%H:%M"),
            "dateTimeFormat": formats.luxon_datetime,
            "hour12": formats.hour12,
            "feedUrl": reverse("planner:calendar_events"),
            "createUrl": reverse("planner:event_create"),
        }
        return context
