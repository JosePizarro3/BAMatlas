"""Admin configuration for public profiles, expertise terms, and audits."""

from django.contrib import admin

from .models import AuditEvent, ExpertiseTerm, Profile, ProfileExpertise
from .services import record_audit_event


class ProfileExpertiseInline(admin.TabularInline):
    """Inline editor for a profile's expertise term relationships."""

    model = ProfileExpertise
    autocomplete_fields = ("term",)
    extra = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Moderation-focused admin for researcher profiles."""

    autocomplete_fields = ("user",)
    inlines = (ProfileExpertiseInline,)
    list_display = (
        "full_name",
        "organizational_entity",
        "job_title",
        "location",
        "is_public",
        "moderation_status",
        "has_pending_updates",
        "updated_at",
    )
    list_filter = (
        "is_public",
        "moderation_status",
        "has_pending_updates",
        "location",
        "organizational_entity",
    )
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "submitted_for_review_at",
        "reviewed_at",
        "reviewed_by",
        "published_at",
        "archived_at",
    )
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "organizational_entity",
        "job_title",
        "research_summary",
    )
    actions = ("publish_profiles", "request_profile_changes", "archive_profiles")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "public_id",
                    "organizational_entity",
                    "job_title",
                    "location",
                    "research_summary",
                    "is_public",
                )
            },
        ),
        (
            "Moderation",
            {
                "fields": (
                    "moderation_status",
                    "has_pending_updates",
                    "submitted_for_review_at",
                    "reviewed_at",
                    "reviewed_by",
                    "published_at",
                    "archived_at",
                    "moderation_notes",
                )
            },
        ),
        ("Important dates", {"fields": ("created_at", "updated_at")}),
    )

    @admin.action(description="Publish selected profiles")
    def publish_profiles(self, request, queryset):
        count = 0
        for profile in queryset.iterator():
            profile.publish(reviewed_by=request.user, notes=profile.moderation_notes)
            record_audit_event(
                actor=request.user,
                target_user=profile.user,
                profile=profile,
                action=AuditEvent.Action.PROFILE_PUBLISHED,
                notes=profile.moderation_notes,
            )
            count += 1
        self.message_user(request, f"Published {count} profile(s).")

    @admin.action(description="Request changes for selected profiles")
    def request_profile_changes(self, request, queryset):
        count = 0
        for profile in queryset.iterator():
            profile.request_changes(reviewed_by=request.user, notes=profile.moderation_notes)
            record_audit_event(
                actor=request.user,
                target_user=profile.user,
                profile=profile,
                action=AuditEvent.Action.PROFILE_CHANGES_REQUESTED,
                notes=profile.moderation_notes,
            )
            count += 1
        self.message_user(request, f"Marked {count} profile(s) for changes.")

    @admin.action(description="Archive selected profiles")
    def archive_profiles(self, request, queryset):
        count = 0
        for profile in queryset.iterator():
            profile.archive(reviewed_by=request.user, notes=profile.moderation_notes)
            record_audit_event(
                actor=request.user,
                target_user=profile.user,
                profile=profile,
                action=AuditEvent.Action.PROFILE_ARCHIVED,
                notes=profile.moderation_notes,
            )
            count += 1
        self.message_user(request, f"Archived {count} profile(s).")

    def has_delete_permission(self, request, obj=None):
        """Disallow destructive profile deletion from the admin."""

        return False


@admin.register(ExpertiseTerm)
class ExpertiseTermAdmin(admin.ModelAdmin):
    """Admin for maintaining the expertise vocabulary table."""

    list_display = ("name", "normalized_name", "is_user_generated", "created_at")
    list_filter = ("is_user_generated",)
    readonly_fields = ("normalized_name", "created_at")
    search_fields = ("name", "normalized_name")

    def has_delete_permission(self, request, obj=None):
        """Disallow destructive expertise deletion from the admin."""

        return False


@admin.register(ProfileExpertise)
class ProfileExpertiseAdmin(admin.ModelAdmin):
    """Admin view of the explicit profile-term relationships."""

    autocomplete_fields = ("profile", "term")
    list_display = ("profile", "term", "created_at")
    search_fields = ("profile__user__first_name", "profile__user__last_name", "term__name")

    def has_delete_permission(self, request, obj=None):
        """Disallow destructive join-row deletion from the admin."""

        return False


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    """Read-only admin for the moderation and account audit trail."""

    autocomplete_fields = ("actor", "target_user", "profile")
    list_display = ("action", "target_user", "profile", "actor", "created_at")
    list_filter = ("action",)
    readonly_fields = ("actor", "target_user", "profile", "action", "notes", "created_at")
    search_fields = ("target_user__email", "profile__user__email", "notes")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
