"""Signals that keep account and directory records in sync."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    """Create a matching profile whenever a new user account is created."""

    if created:
        Profile.objects.get_or_create(user=instance)
