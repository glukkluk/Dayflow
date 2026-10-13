from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "timezone", "work_start", "work_end", "buffer_minutes")
    list_select_related = ("user",)
    search_fields = ("user__username",)
