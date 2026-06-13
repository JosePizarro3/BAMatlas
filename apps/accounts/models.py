from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    is_approved = models.BooleanField(
        default=False,
        help_text="Admins can use this to moderate first-time account activation.",
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    deactivated_at = models.DateTimeField(blank=True, null=True)
    deactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="deactivated_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def __str__(self) -> str:
        return self.email

    def mark_email_verified(self, *, save: bool = True) -> None:
        if not self.is_email_verified:
            self.is_email_verified = True
            self.email_verified_at = timezone.now()
            if save:
                self.save(update_fields=["is_email_verified", "email_verified_at", "updated_at"])

    def mark_approved(self, *, save: bool = True) -> None:
        if not self.is_approved:
            self.is_approved = True
            self.approved_at = timezone.now()
            if save:
                self.save(update_fields=["is_approved", "approved_at", "updated_at"])

    def deactivate(self, *, by_user=None, save: bool = True) -> None:
        if self.is_active:
            self.is_active = False
            self.deactivated_at = timezone.now()
            self.deactivated_by = by_user
            if save:
                self.save(
                    update_fields=["is_active", "deactivated_at", "deactivated_by", "updated_at"]
                )

    def reactivate(self, *, save: bool = True) -> None:
        if not self.is_active:
            self.is_active = True
            self.deactivated_at = None
            self.deactivated_by = None
            if save:
                self.save(
                    update_fields=["is_active", "deactivated_at", "deactivated_by", "updated_at"]
                )
