from django.apps import AppConfig


class PlannerConfig(AppConfig):
    name = "planner"
    verbose_name = "Планувальник"

    def ready(self):
        from . import signals  # noqa: F401
