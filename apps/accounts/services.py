"""Service helpers for account verification and outbound email."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


def build_email_verification_url(user, request):
    """Build the absolute verification link for a user."""

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return request.build_absolute_uri(reverse("accounts:verify-email", args=[uid, token]))


def send_verification_email(user, request):
    """Render and send the account verification email."""

    verification_url = build_email_verification_url(user, request)
    context = {
        "user": user,
        "verification_url": verification_url,
        "require_admin_approval": settings.ACCOUNT_REQUIRE_ADMIN_APPROVAL,
    }
    subject = render_to_string("accounts/emails/verify_subject.txt", context).strip()
    body = render_to_string("accounts/emails/verify_body.txt", context)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])


def get_pending_verification_user(email: str):
    """Return an active user that still needs email verification."""

    return User.objects.filter(
        email__iexact=email,
        is_email_verified=False,
        is_active=True,
    ).first()


def send_verification_email_if_pending(email: str, request) -> bool:
    """Send a verification email only when the address belongs to a pending account."""

    user = get_pending_verification_user(email)
    if user is None:
        return False
    send_verification_email(user, request)
    return True
