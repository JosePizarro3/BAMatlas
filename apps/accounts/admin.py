from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.directory.models import AuditEvent

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "is_staff",
        "is_active",
        "is_email_verified",
        "is_approved",
        "deactivated_at",
        "approved_at",
        "created_at",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "is_email_verified", "is_approved")
    search_fields = ("email",)
    readonly_fields = (
        "last_login",
        "date_joined",
        "created_at",
        "updated_at",
        "email_verified_at",
        "approved_at",
        "deactivated_at",
        "deactivated_by",
    )
    actions = ("approve_selected_users", "deactivate_selected_users", "reactivate_selected_users")

    fieldsets = (
        (None, {"fields": ("email", "password", "first_name", "last_name")}),
        (
            "Access",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Verification",
            {"fields": ("is_email_verified", "email_verified_at", "is_approved", "approved_at")},
        ),
        ("Deactivation", {"fields": ("deactivated_at", "deactivated_by")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    @admin.action(description="Approve selected users")
    def approve_selected_users(self, request, queryset):
        approved_count = 0
        for user in queryset.iterator():
            if not user.is_approved:
                user.mark_approved()
                AuditEvent.objects.create(
                    actor=request.user,
                    target_user=user,
                    action=AuditEvent.Action.USER_APPROVED,
                )
                approved_count += 1
        self.message_user(request, f"Approved {approved_count} user(s).")

    @admin.action(description="Deactivate selected users")
    def deactivate_selected_users(self, request, queryset):
        deactivated_count = 0
        for user in queryset.iterator():
            if user != request.user and user.is_active:
                user.deactivate(by_user=request.user)
                AuditEvent.objects.create(
                    actor=request.user,
                    target_user=user,
                    action=AuditEvent.Action.USER_DEACTIVATED,
                )
                deactivated_count += 1
        self.message_user(request, f"Deactivated {deactivated_count} user(s).")

    @admin.action(description="Reactivate selected users")
    def reactivate_selected_users(self, request, queryset):
        reactivated_count = 0
        for user in queryset.iterator():
            if not user.is_active:
                user.reactivate()
                AuditEvent.objects.create(
                    actor=request.user,
                    target_user=user,
                    action=AuditEvent.Action.USER_REACTIVATED,
                )
                reactivated_count += 1
        self.message_user(request, f"Reactivated {reactivated_count} user(s).")

    def has_delete_permission(self, request, obj=None):
        return False
