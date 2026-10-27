from django import template
from django.template.defaultfilters import date as date_filter
from django.utils.translation import override

from ..models import Notification

register = template.Library()


@register.filter(expects_localtime=True)
def profile_date(value, format_string):
    """Render in the active profile timezone, spelling AM/PM in English."""
    # Calling date_filter directly doesn't apply its expects_localtime flag;
    # our filter must request timezone conversion from the template engine too.
    if "A" in format_string:
        with override("en"):
            return date_filter(value, format_string)
    return date_filter(value, format_string)


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
