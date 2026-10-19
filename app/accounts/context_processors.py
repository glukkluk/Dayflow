from .formats import get_formats


def display_formats(request):
    """Expose the user's date/time formats to templates for ``|date:...``."""
    user = getattr(request, "user", None)
    profile = user.profile if user is not None and user.is_authenticated else None
    formats = get_formats(profile)
    return {
        "date_fmt": formats.date,
        "short_date_fmt": formats.short_date,
        "time_fmt": formats.time,
        "datetime_fmt": formats.datetime,
        "short_datetime_fmt": formats.short_datetime,
    }
