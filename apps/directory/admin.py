from django.contrib import admin

from .models import ExpertiseTerm, Profile, ProfileExpertise


class ProfileExpertiseInline(admin.TabularInline):
    model = ProfileExpertise
    autocomplete_fields = ("term",)
    extra = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    autocomplete_fields = ("user",)
    inlines = (ProfileExpertiseInline,)
    list_display = (
        "full_name",
        "organizational_entity",
        "job_title",
        "location",
        "is_public",
        "updated_at",
    )
    list_filter = ("is_public", "location", "organizational_entity")
    readonly_fields = ("public_id", "created_at", "updated_at")
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
        "organizational_entity",
        "job_title",
        "research_summary",
    )


@admin.register(ExpertiseTerm)
class ExpertiseTermAdmin(admin.ModelAdmin):
    list_display = ("name", "normalized_name", "is_user_generated", "created_at")
    list_filter = ("is_user_generated",)
    readonly_fields = ("normalized_name", "created_at")
    search_fields = ("name", "normalized_name")


@admin.register(ProfileExpertise)
class ProfileExpertiseAdmin(admin.ModelAdmin):
    autocomplete_fields = ("profile", "term")
    list_display = ("profile", "term", "created_at")
    search_fields = ("profile__user__first_name", "profile__user__last_name", "term__name")
