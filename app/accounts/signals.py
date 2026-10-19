from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, raw, using, **kwargs):
    if created and not raw:
        Profile.objects.using(using).get_or_create(user=instance)  # ty: ignore[unresolved-attribute]


@receiver(post_delete, sender=Profile)
def delete_avatar_file(sender, instance, **kwargs):
    """Remove the uploaded file together with the profile (e.g. account deletion)."""
    if instance.avatar:
        instance.avatar.delete(save=False)
