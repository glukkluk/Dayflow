from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import url_has_allowed_host_and_scheme
from social_core.exceptions import AuthCanceled


class GoogleAuthCancellationMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if not isinstance(exception, AuthCanceled):
            return None
        if getattr(getattr(request, "backend", None), "name", None) != "google-oauth2":
            return None

        messages.info(request, "Вхід через Google скасовано. Ви можете спробувати ще раз.")
        login_url = reverse("accounts:login")
        next_url = request.session.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            login_url += "?" + urlencode({"next": next_url})
        return redirect(login_url)


class ProfileTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_timezone = (
            ZoneInfo(request.user.profile.timezone)
            if request.user.is_authenticated
            else ZoneInfo("UTC")
        )
        with timezone.override(user_timezone):
            return self.get_response(request)
