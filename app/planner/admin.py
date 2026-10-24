from django.contrib import admin

from .models import Category, Event, Notification, Task


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "user")
    list_select_related = ("user",)
    list_filter = ("user",)
    search_fields = ("name", "user__username")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "start", "end", "all_day", "recurrence", "category")
    list_select_related = ("user", "category")
    list_filter = ("all_day", "recurrence", "category")
    search_fields = ("title", "description", "user__username")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "priority", "deadline", "estimated_minutes", "category")
    list_select_related = ("user", "category")
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description", "user__username")
    readonly_fields = ("completed_at", "created_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "kind", "created_at", "read_at")
    list_select_related = ("user",)
    list_filter = ("kind",)
    search_fields = ("message", "user__username")
    readonly_fields = ("created_at", "delivered_at", "occurrence_start")
