import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from ..models import Notification
from ..services.notifications import collect_due, serialize


class _JsonBodyMixin:
    def read_json(self, request):
        try:
            data = json.loads(request.body)
        except ValueError, UnicodeDecodeError:
            return None
        return data if isinstance(data, dict) else None


class NotificationsPageView(LoginRequiredMixin, TemplateView):
    template_name = "planner/notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["results"] = Notification.objects.filter(user=self.request.user)[:100]
        context["unread"] = Notification.objects.filter(
            user=self.request.user, read_at__isnull=True
        ).count()
        return context

    def post(self, request):
        """Plain POST: mark everything read and return to the list."""
        Notification.objects.filter(user=request.user, read_at__isnull=True).update(
            read_at=timezone.now()
        )
        return redirect(reverse_lazy("planner:notifications"))


class PendingNotificationsView(LoginRequiredMixin, View):
    """Unread reminders for the polling badge/toast widget.

    Generating and listing are combined: each poll also materializes any
    reminders that became due, so a missed poll never loses a reminder.
    """

    http_method_names = ["get", "head", "options"]

    def get(self, request):
        collect_due(request.user)
        notifications = Notification.objects.filter(
            user=request.user, read_at__isnull=True
        )[:50]
        return JsonResponse([serialize(item) for item in notifications], safe=False)


class NotificationListView(LoginRequiredMixin, View):
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user)[:100]
        return JsonResponse(
            {
                "results": [serialize(item) for item in notifications],
                "unread": Notification.objects.filter(
                    user=request.user, read_at__isnull=True
                ).count(),
            },
            safe=False,
        )


class ReadNotificationsView(LoginRequiredMixin, _JsonBodyMixin, View):
    """Mark the given ids, or every notification, as read."""

    http_method_names = ["post", "options"]

    def post(self, request):
        data = self.read_json(request)
        if data is None:
            return JsonResponse({"errors": ["Очікується JSON-об'єкт."]}, status=400)
        if data.get("all") is True:
            Notification.objects.filter(user=request.user, read_at__isnull=True).update(
                read_at=timezone.now()
            )
            return JsonResponse({"unread": 0})
        ids = data.get("ids", [])
        if not isinstance(ids, list) or not all(type(item) is int for item in ids):
            return JsonResponse(
                {"errors": ["ids має бути списком цілих чисел."]}, status=400
            )
        Notification.objects.filter(
            user=request.user, pk__in=ids, read_at__isnull=True
        ).update(read_at=timezone.now())
        return JsonResponse(
            {
                "unread": Notification.objects.filter(
                    user=request.user, read_at__isnull=True
                ).count()
            }
        )
