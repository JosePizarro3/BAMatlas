import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse

from .services import clean_expertise_display_name, normalize_expertise_name


class ExpertiseTerm(models.Model):
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
        self.name = clean_expertise_display_name(self.name)
        self.normalized_name = normalize_expertise_name(self.name)
        super().save(*args, **kwargs)


class Profile(models.Model):
    class Location(models.TextChoices):
        UE = "UE", "UE"
        AH = "AH", "AH"
        TTS = "TTS", "TTS"

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


class ProfileExpertise(models.Model):
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
