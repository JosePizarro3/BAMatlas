"""Forms for registration, login, and email-verification flows."""

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError

User = get_user_model()


class RegistrationForm(UserCreationForm):
    """Create a local BAMatlas account for a BAM email address."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs["autocomplete"] = "given-name"
        self.fields["last_name"].widget.attrs["autocomplete"] = "family-name"
        self.fields["email"].widget = forms.EmailInput(attrs={"autocomplete": "email"})

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        allowed_domains = {domain.lower() for domain in settings.ACCOUNT_ALLOWED_EMAIL_DOMAINS}
        email_domain = email.rsplit("@", 1)[-1]
        if email_domain not in allowed_domains:
            domains = ", ".join(sorted(allowed_domains))
            raise ValidationError(f"Use an institutional email address from: {domains}.")
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_email_verified = False
        user.is_approved = False
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """Authentication form that surfaces moderation-related account states."""

    username = forms.EmailField(
        label="Institutional email",
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        "email_unverified": "Verify your email address before signing in.",
        "approval_pending": "Your account is waiting for administrator approval.",
        "inactive": "This account has been disabled. Contact an administrator for help.",
    }

    def clean(self):
        try:
            return super().clean()
        except ValidationError as exc:
            email = self.cleaned_data.get("username", "").strip().lower()
            user = User.objects.filter(email__iexact=email, is_active=False).first()
            password = self.cleaned_data.get("password")
            if user is not None and password and user.check_password(password):
                raise ValidationError(self.error_messages["inactive"], code="inactive") from exc
            raise exc

    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise ValidationError(self.error_messages["inactive"], code="inactive")
        if not user.is_email_verified:
            raise ValidationError(self.error_messages["email_unverified"], code="email_unverified")
        if settings.ACCOUNT_REQUIRE_ADMIN_APPROVAL and not user.is_approved:
            raise ValidationError(self.error_messages["approval_pending"], code="approval_pending")


class ResendVerificationEmailForm(forms.Form):
    """Collect an institutional email to resend a verification link."""

    email = forms.EmailField(
        label="Institutional email",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
