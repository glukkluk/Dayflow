from django import template

from ..models import Notification

register = template.Library()


@register.simple_tag(takes_context=True)
def unread_count(context):
    """Кількість непрочитаних сповіщень поточного користувача (для значка в меню)."""
    request = context.get("request")
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return 0
    return Notification.objects.filter(user=user, read_at__isnull=True).count()  # ty: ignore[unresolved-attribute]


@register.inclusion_tag("planner/partials/pagination.html", takes_context=True)
def pagination(context, page_obj, label="Сторінки"):
    """Єдина пагінація для списків; зберігає решту GET-параметрів (пошук, фільтри)."""
    return {"page_obj": page_obj, "label": label, "request": context["request"]}
