"""Per-user date/time display formats (Django ``date`` filter syntax + Luxon)."""

from dataclasses import dataclass

from .models import Profile


@dataclass(frozen=True)
class DisplayFormats:
    date: str  # 31.12.2026
    short_date: str  # 31.12 (no year)
    time: str  # 14:30 / 2:30 PM
    luxon_date: str
    luxon_time: str
    hour12: bool

    @property
    def datetime(self):
        return f"{self.date} {self.time}"

    @property
    def short_datetime(self):
        return f"{self.short_date} {self.time}"

    @property
    def luxon_datetime(self):
        return f"{self.luxon_date} {self.luxon_time}"


# date format -> (full, short, luxon)
_DATES = {
    Profile.DateFormat.DMY_DOT: ("d.m.Y", "d.m", "dd.LL.yyyy"),
    Profile.DateFormat.DMY_SLASH: ("d/m/Y", "d/m", "dd/LL/yyyy"),
    Profile.DateFormat.MDY_SLASH: ("m/d/Y", "m/d", "LL/dd/yyyy"),
    Profile.DateFormat.YMD_DASH: ("Y-m-d", "m-d", "yyyy-LL-dd"),
}
# time format -> (django, luxon)
_TIMES = {
    Profile.TimeFormat.H24: ("H:i", "HH:mm"),
    Profile.TimeFormat.H12: ("g:i A", "h:mm a"),
}


def get_formats(profile=None):
    date_key = getattr(profile, "date_format", Profile.DateFormat.DMY_DOT)
    time_key = getattr(profile, "time_format", Profile.TimeFormat.H24)
    full, short, luxon_date = _DATES.get(date_key, _DATES[Profile.DateFormat.DMY_DOT])
    clock, luxon_time = _TIMES.get(time_key, _TIMES[Profile.TimeFormat.H24])
    return DisplayFormats(
        date=full,
        short_date=short,
        time=clock,
        luxon_date=luxon_date,
        luxon_time=luxon_time,
        hour12=time_key == Profile.TimeFormat.H12,
    )
