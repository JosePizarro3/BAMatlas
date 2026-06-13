"""Directory models for public profiles, expertise terms, and moderation history."""

import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .services import clean_expertise_display_name, normalize_expertise_name


class ExpertiseTerm(models.Model):
    """Reusable expertise vocabulary item shown in search and autocomplete."""

    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, unique=True, db_index=True)
    is_user_generated = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_expertise_terms",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        """Normalise the stored name before persisting the term."""

        self.name = clean_expertise_display_name(self.name)
        self.normalized_name = normalize_expertise_name(self.name)
        super().save(*args, **kwargs)


class Profile(models.Model):
    """Public-facing metadata about a BAM researcher."""

    class Location(models.TextChoices):
        UE = "UE", "UE"
        AH = "AH", "AH"
        TTS = "TTS", "TTS"

    class ModerationStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_REVIEW = "pending_review", "Pending review"
        PUBLISHED = "published", "Published"
        CHANGES_REQUESTED = "changes_requested", "Changes requested"
        ARCHIVED = "archived", "Archived"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    organizational_entity = models.CharField(max_length=255, blank=True, db_index=True)
    job_title = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=3, blank=True, choices=Location.choices)
    research_summary = models.TextField(blank=True, max_length=1200)
    is_public = models.BooleanField(
        default=True,
        help_text="Controls whether this profile appears in public directory views.",
    )
    moderation_status = models.CharField(
        max_length=32,
        choices=ModerationStatus.choices,
        default=ModerationStatus.DRAFT,
        db_index=True,
    )
    has_pending_updates = models.BooleanField(default=False)
    submitted_for_review_at = models.DateTimeField(blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_profiles",
    )
    published_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)
    moderation_notes = models.TextField(blank=True)
    expertise_terms = models.ManyToManyField(
        ExpertiseTerm,
        blank=True,
        through="ProfileExpertise",
        related_name="profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__last_name", "user__first_name", "user__email")

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        return self.user.get_full_name() or self.user.email

    def get_absolute_url(self):
        return reverse("directory:profile-detail", args=[str(self.public_id)])

    @property
    def is_listed_publicly(self) -> bool:
        """Return whether the profile is visible in public directory views."""

        return self.is_public and self.moderation_status == self.ModerationStatus.PUBLISHED

    def submit_for_review(self, *, save: bool = True) -> None:
        """Transition the profile into the appropriate moderation state."""

        now = timezone.now()
        if self.is_public:
            if self.moderation_status == self.ModerationStatus.PUBLISHED:
                self.has_pending_updates = True
            else:
                self.moderation_status = self.ModerationStatus.PENDING_REVIEW
                self.has_pending_updates = False
            self.submitted_for_review_at = now
        else:
            self.moderation_status = self.ModerationStatus.DRAFT
            self.has_pending_updates = False

        if save:
            self.save(
                update_fields=[
                    "is_public",
                    "moderation_status",
                    "has_pending_updates",
                    "submitted_for_review_at",
                    "updated_at",
                ]
            )

    def publish(self, *, reviewed_by=None, notes: str = "", save: bool = True) -> None:
        """Mark a profile as publicly visible and moderation-complete."""

        now = timezone.now()
        self.is_public = True
        self.moderation_status = self.ModerationStatus.PUBLISHED
        self.has_pending_updates = False
        self.reviewed_at = now
        self.reviewed_by = reviewed_by
        self.published_at = self.published_at or now
        self.archived_at = None
        self.moderation_notes = notes
        if save:
            self.save(
                update_fields=[
                    "is_public",
                    "moderation_status",
                    "has_pending_updates",
                    "reviewed_at",
                    "reviewed_by",
                    "published_at",
                    "archived_at",
                    "moderation_notes",
                    "updated_at",
                ]
            )

    def request_changes(self, *, reviewed_by=None, notes: str = "", save: bool = True) -> None:
        """Send a profile back to the owner without making it public."""

        now = timezone.now()
        # Keep the user's intent to publish; visibility still stays off because
        # only published profiles are exposed publicly.
        self.is_public = True
        self.moderation_status = self.ModerationStatus.CHANGES_REQUESTED
        self.has_pending_updates = False
        self.reviewed_at = now
        self.reviewed_by = reviewed_by
        self.moderation_notes = notes
        if save:
            self.save(
                update_fields=[
                    "is_public",
                    "moderation_status",
                    "has_pending_updates",
                    "reviewed_at",
                    "reviewed_by",
                    "moderation_notes",
                    "updated_at",
                ]
            )

    def archive(self, *, reviewed_by=None, notes: str = "", save: bool = True) -> None:
        """Remove a profile from the public directory while retaining the record."""

        now = timezone.now()
        self.is_public = False
        self.moderation_status = self.ModerationStatus.ARCHIVED
        self.has_pending_updates = False
        self.reviewed_at = now
        self.reviewed_by = reviewed_by
        self.archived_at = now
        self.moderation_notes = notes
        if save:
            self.save(
                update_fields=[
                    "is_public",
                    "moderation_status",
                    "has_pending_updates",
                    "reviewed_at",
                    "reviewed_by",
                    "archived_at",
                    "moderation_notes",
                    "updated_at",
                ]
            )


class ProfileExpertise(models.Model):
    """Explicit join model between profiles and expertise terms."""

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    term = models.ForeignKey(ExpertiseTerm, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("profile", "term"), name="unique_profile_expertise"),
        ]
        ordering = ("term__name",)

    def __str__(self) -> str:
        return f"{self.profile.full_name} - {self.term.name}"


class AuditEvent(models.Model):
    """Append-only audit trail for moderation and account actions."""

    class Action(models.TextChoices):
        USER_APPROVED = "user_approved", "User approved"
        USER_DEACTIVATED = "user_deactivated", "User deactivated"
        USER_REACTIVATED = "user_reactivated", "User reactivated"
        PROFILE_SUBMITTED = "profile_submitted", "Profile submitted"
        PROFILE_PUBLISHED = "profile_published", "Profile published"
        PROFILE_CHANGES_REQUESTED = "profile_changes_requested", "Profile changes requested"
        PROFILE_ARCHIVED = "profile_archived", "Profile archived"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_targets",
    )
    profile = models.ForeignKey(
        Profile,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    action = models.CharField(max_length=64, choices=Action.choices)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.get_action_display()} at {self.created_at:%Y-%m-%d %H:%M}"
