from django.urls import path

from .views import (
    autoplan,
    calendar,
    calendar_api,
    categories,
    dashboard,
    events,
    free_tasks,
    notifications,
    tasks,
)

app_name = "planner"

urlpatterns = [
    path("", dashboard.DashboardView.as_view(), name="dashboard"),
    path(
        "notifications/",
        notifications.NotificationsPageView.as_view(),
        name="notifications",
    ),
    path(
        "api/notifications/pending/",
        notifications.PendingNotificationsView.as_view(),
        name="pending_notifications",
    ),
    path(
        "api/notifications/read/",
        notifications.ReadNotificationsView.as_view(),
        name="read_notifications",
    ),
    path("tasks/autoplan/", autoplan.AutoplanView.as_view(), name="task_autoplan"),
    path("calendar/", calendar.CalendarView.as_view(), name="calendar"),
    path(
        "api/events/<int:pk>/move/",
        calendar_api.EventMoveView.as_view(),
        name="event_move",
    ),
    path(
        "api/events/check-conflicts/",
        calendar_api.CheckConflictsView.as_view(),
        name="check_conflicts",
    ),
    path(
        "api/events/", calendar_api.CalendarEventsView.as_view(), name="calendar_events"
    ),
    path("tasks/", tasks.TaskListView.as_view(), name="task_list"),
    path("tasks/free/", free_tasks.FreeTaskSuggestionsView.as_view(), name="free_tasks"),
    path("tasks/<int:pk>/take/", free_tasks.FreeTaskTakeView.as_view(), name="task_take"),
    path("tasks/new/", tasks.TaskCreateView.as_view(), name="task_create"),
    path("tasks/<int:pk>/edit/", tasks.TaskEditView.as_view(), name="task_edit"),
    path("tasks/<int:pk>/delete/", tasks.TaskDeleteView.as_view(), name="task_delete"),
    path("tasks/<int:pk>/toggle/", tasks.TaskToggleView.as_view(), name="task_toggle"),
    path("categories/", categories.CategoryListView.as_view(), name="category_list"),
    path(
        "categories/new/",
        categories.CategoryCreateView.as_view(),
        name="category_create",
    ),
    path(
        "categories/<int:pk>/edit/",
        categories.CategoryEditView.as_view(),
        name="category_edit",
    ),
    path(
        "categories/<int:pk>/delete/",
        categories.CategoryDeleteView.as_view(),
        name="category_delete",
    ),
    path("events/", events.EventListView.as_view(), name="event_list"),
    path("events/new/", events.EventCreateView.as_view(), name="event_create"),
    path(
        "events/<int:pk>/details/",
        events.EventDetailView.as_view(),
        name="event_detail",
    ),
    path("events/<int:pk>/edit/", events.EventEditView.as_view(), name="event_edit"),
    path(
        "events/<int:pk>/delete/", events.EventDeleteView.as_view(), name="event_delete"
    ),
]
