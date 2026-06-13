"""Views for the public expertise directory and moderation operations."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from .forms import ProfileForm
from .models import AuditEvent, Profile
from .services import (
    FEATURED_EXPERTISE_LIMIT,
    filter_public_profiles,
    format_expertise_names,
    get_expertise_suggestions,
    get_featured_expertise_terms,
    get_public_profile_queryset,
    parse_expertise_names,
    record_audit_event,
)


class DirectoryListView(ListView):
    """Landing page and directory listing filtered by expertise."""

    context_object_name = "profiles"
    model = Profile
    paginate_by = 12
    template_name = "directory/directory_list.html"

    def get_queryset(self):
        return filter_public_profiles(expertise=self.request.GET.get("expertise", "").strip())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_expertise_terms = parse_expertise_names(
            self.request.GET.get("expertise", "").strip()
        )
        context["featured_terms"] = get_featured_expertise_terms(limit=FEATURED_EXPERTISE_LIMIT)
        context["search_expertise"] = format_expertise_names(selected_expertise_terms)
        context["result_count"] = self.get_queryset().count()
        return context


class ProfileDetailView(DetailView):
    """Public profile detail page for a published researcher profile."""

    context_object_name = "profile"
    template_name = "directory/profile_detail.html"

    def get_queryset(self):
        return get_public_profile_queryset()

    def get_object(self, queryset=None):
        queryset = queryset or self.get_queryset()
        return queryset.get(public_id=self.kwargs["public_id"])


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Self-service editor for the signed-in user's profile."""

    form_class = ProfileForm
    template_name = "directory/profile_form.html"

    def get_object(self, queryset=None):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        profile = self.object
        if (
            profile.moderation_status == Profile.ModerationStatus.PUBLISHED
            and profile.has_pending_updates
        ):
            messages.success(
                self.request,
                (
                    "Your profile changes were saved and flagged for admin review "
                    "while remaining public."
                ),
            )
        elif profile.moderation_status == Profile.ModerationStatus.PENDING_REVIEW:
            messages.success(
                self.request,
                "Your profile has been submitted for admin review before public listing.",
            )
        else:
            messages.success(self.request, "Your public profile has been updated.")
        record_audit_event(
            actor=self.request.user,
            target_user=self.request.user,
            profile=profile,
            action=AuditEvent.Action.PROFILE_SUBMITTED,
        )
        return response

    def get_success_url(self):
        if self.object.is_listed_publicly:
            return self.object.get_absolute_url()
        return reverse("accounts:account-home")


class ExpertiseSuggestionView(View):
    """Autocomplete endpoint for expertise terms visible in the public directory."""

    def get(self, request, *args, **kwargs):
        query = request.GET.get("q", "").strip()
        return JsonResponse({"results": get_expertise_suggestions(query=query)})


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict a view to staff users while keeping normal login redirects."""

    raise_exception = True

    def test_func(self):
        return self.request.user.is_staff


class ModerationDashboardView(StaffRequiredMixin, TemplateView):
    """Simple staff dashboard for approvals, moderation, and audit review."""

    template_name = "directory/moderation_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.accounts.models import User

        context["pending_users"] = User.objects.filter(
            is_active=True,
            is_email_verified=True,
            is_approved=False,
        ).order_by("created_at")
        context["pending_profiles"] = (
            Profile.objects.select_related("user")
            .filter(moderation_status=Profile.ModerationStatus.PENDING_REVIEW)
            .order_by("submitted_for_review_at", "updated_at")
        )
        context["profiles_with_pending_updates"] = (
            Profile.objects.select_related("user")
            .filter(
                moderation_status=Profile.ModerationStatus.PUBLISHED,
                has_pending_updates=True,
            )
            .order_by("submitted_for_review_at", "updated_at")
        )
        context["recent_events"] = AuditEvent.objects.select_related(
            "actor", "target_user", "profile"
        )[:20]
        return context

    def post(self, request, *args, **kwargs):
        from apps.accounts.models import User

        action = request.POST.get("action")
        notes = request.POST.get("notes", "").strip()

        if action == "approve-user":
            user = User.objects.get(pk=request.POST["user_id"])
            user.mark_approved()
            record_audit_event(
                actor=request.user,
                target_user=user,
                action=AuditEvent.Action.USER_APPROVED,
                notes=notes,
            )
            messages.success(request, f"Approved {user.email}.")
        elif action == "deactivate-user":
            user = User.objects.get(pk=request.POST["user_id"])
            if user != request.user:
                user.deactivate(by_user=request.user)
                record_audit_event(
                    actor=request.user,
                    target_user=user,
                    action=AuditEvent.Action.USER_DEACTIVATED,
                    notes=notes,
                )
                messages.success(request, f"Deactivated {user.email}.")
        elif action == "reactivate-user":
            user = User.objects.get(pk=request.POST["user_id"])
            user.reactivate()
            record_audit_event(
                actor=request.user,
                target_user=user,
                action=AuditEvent.Action.USER_REACTIVATED,
                notes=notes,
            )
            messages.success(request, f"Reactivated {user.email}.")
        elif action == "publish-profile":
            profile = Profile.objects.get(pk=request.POST["profile_id"])
            profile.publish(reviewed_by=request.user, notes=notes)
            record_audit_event(
                actor=request.user,
                target_user=profile.user,
                profile=profile,
                action=AuditEvent.Action.PROFILE_PUBLISHED,
                notes=notes,
            )
            messages.success(request, f"Published {profile.full_name}.")
        elif action == "request-profile-changes":
            profile = Profile.objects.get(pk=request.POST["profile_id"])
            profile.request_changes(reviewed_by=request.user, notes=notes)
            record_audit_event(
                actor=request.user,
                target_user=profile.user,
                profile=profile,
                action=AuditEvent.Action.PROFILE_CHANGES_REQUESTED,
                notes=notes,
            )
            messages.success(request, f"Requested changes from {profile.full_name}.")
        elif action == "archive-profile":
            profile = Profile.objects.get(pk=request.POST["profile_id"])
            profile.archive(reviewed_by=request.user, notes=notes)
            record_audit_event(
                actor=request.user,
                target_user=profile.user,
                profile=profile,
                action=AuditEvent.Action.PROFILE_ARCHIVED,
                notes=notes,
            )
            messages.success(request, f"Archived {profile.full_name}.")

        return redirect("directory:moderation-dashboard")
