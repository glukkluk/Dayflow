from django.urls import path

from .views import categories, events

app_name = "planner"

urlpatterns = [
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
