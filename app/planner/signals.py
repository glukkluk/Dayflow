from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Category

DEFAULT_CATEGORIES = (
    ("Робота", "#3B82F6"),
    ("Навчання", "#8B5CF6"),
    ("Здоров'я", "#22C55E"),
    ("Відпочинок", "#F59E0B"),
    ("Особисте", "#EC4899"),
)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_categories(sender, instance, created, raw, using, **kwargs):
    if created and not raw:
        Category.objects.using(using).bulk_create(  # ty: ignore[unresolved-attribute]
            [
                Category(user=instance, name=name, color=color)
                for name, color in DEFAULT_CATEGORIES
            ]
        )
