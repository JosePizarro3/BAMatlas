from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.generic import FormView, TemplateView

from .forms import RegistrationForm, ResendVerificationEmailForm
from .services import send_verification_email

User = get_user_model()


class RegisterView(FormView):
    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:registration-pending")

    def form_valid(self, form):
        user = form.save()
        send_verification_email(user, self.request)
        self.request.session["pending_registration_email"] = user.email
        return super().form_valid(form)


class RegistrationPendingView(FormView):
    form_class = ResendVerificationEmailForm
    template_name = "accounts/registration_pending.html"
    success_url = reverse_lazy("accounts:registration-pending")

    def get_initial(self):
        initial = super().get_initial()
        initial["email"] = self.request.session.get("pending_registration_email", "")
        return initial

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        user = User.objects.filter(
            email__iexact=email,
            is_email_verified=False,
            is_active=True,
        ).first()
        if user is not None:
            send_verification_email(user, self.request)
        messages.success(
            self.request,
            (
                "If that account exists and is still unverified, "
                "a fresh verification email has been sent."
            ),
        )
        return super().form_valid(form)


class ResendVerificationEmailView(FormView):
    form_class = ResendVerificationEmailForm
    success_url = reverse_lazy("accounts:registration-pending")

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        user = User.objects.filter(
            email__iexact=email,
            is_email_verified=False,
            is_active=True,
        ).first()
        if user is not None:
            send_verification_email(user, self.request)
        messages.success(
            self.request,
            (
                "If that account exists and is still unverified, "
                "a fresh verification email has been sent."
            ),
        )
        return redirect(self.get_success_url())


class VerifyEmailView(TemplateView):
    template_name = "accounts/verify_result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self._get_user()
        if user is None:
            context["verification_state"] = "invalid"
            return context

        if default_token_generator.check_token(user, self.kwargs["token"]):
            if not user.is_email_verified:
                user.mark_email_verified()
            context["verification_state"] = (
                "approved"
                if (not settings.ACCOUNT_REQUIRE_ADMIN_APPROVAL or user.is_approved)
                else "pending-approval"
            )
            return context

        context["verification_state"] = "invalid"
        return context

    def _get_user(self):
        try:
            uid = force_str(urlsafe_base64_decode(self.kwargs["uidb64"]))
            return User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None


class AccountHomeView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/account_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.directory.models import Profile

        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        context["profile"] = profile
        return context
