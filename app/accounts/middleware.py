from zoneinfo import ZoneInfo

from django.utils import timezone


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
