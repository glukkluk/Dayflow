from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import ListView

from ..models import Event
from ..roles import VIEW_ALL_EVENTS


class AllEventsView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Події всіх користувачів — лише для ролі «Менеджер».

    Право перевіряється на сервері: без нього авторизований користувач
    отримує 403, незалежно від того, чи показано посилання в меню.
    """

    model = Event
    permission_required = VIEW_ALL_EVENTS
    template_name = "planner/all_events.html"
    context_object_name = "events"
    paginate_by = 20

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return render(self.request, "error_page.html", {
                "code": "403",
                "heading": "Доступ обмежено",
                "message": "У вас немає дозволу переглядати цю сторінку. Якщо вважаєте, що це помилка, зверніться до адміністратора.",
            }, status=403)
        return super().handle_no_permission()

    def get_queryset(self):
        events = (
            super()
            .get_queryset()
            .select_related("user", "category")
            .order_by("-start", "pk")
        )
        self.query = self.request.GET.get("q", "").strip()
        self.owner_filter = self.request.GET.get("owner", "")
        if self.owner_filter == "mine":
            events = events.filter(user=self.request.user)
        elif self.owner_filter == "others":
            events = events.exclude(user=self.request.user)
        if self.query:
            events = events.filter(
                Q(title__icontains=self.query) | Q(user__username__icontains=self.query)
            )
        return events

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.query
        context["owner_filter"] = self.owner_filter
        return context
