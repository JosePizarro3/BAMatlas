import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()
pytestmark = pytest.mark.django_db


def build_verification_path(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return reverse("accounts:verify-email", args=[uid, token])


def test_registration_creates_pending_user_and_sends_verification_email():
    client = Client()

    response = client.post(
        reverse("accounts:register"),
        {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@bam.de",
            "password1": "HighlySecurePass123!!",
            "password2": "HighlySecurePass123!!",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("accounts:registration-pending")
    user = User.objects.get(email="ada@bam.de")
    assert user.first_name == "Ada"
    assert user.is_email_verified is False
    assert user.is_approved is False
    assert len(mail.outbox) == 1
    assert "Verify your BAMatlas account" in mail.outbox[0].subject
    assert build_verification_path(user) in mail.outbox[0].body


def test_registration_rejects_non_bam_email_addresses():
    client = Client()

    response = client.post(
        reverse("accounts:register"),
        {
            "first_name": "Grace",
            "last_name": "Hopper",
            "email": "grace@example.com",
            "password1": "HighlySecurePass123!!",
            "password2": "HighlySecurePass123!!",
        },
    )

    assert response.status_code == 200
    assert b"Use an institutional email address" in response.content
    assert User.objects.filter(email="grace@example.com").exists() is False


@override_settings(ACCOUNT_REQUIRE_ADMIN_APPROVAL=False)
def test_verified_user_can_sign_in_when_admin_approval_is_disabled():
    user = User.objects.create_user(
        email="verified@bam.de",
        password="HighlySecurePass123!!",
        first_name="Verified",
        last_name="User",
    )
    client = Client()

    verify_response = client.get(build_verification_path(user))

    user.refresh_from_db()
    assert verify_response.status_code == 200
    assert user.is_email_verified is True

    login_response = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "HighlySecurePass123!!"},
    )

    assert login_response.status_code == 302
    assert login_response.headers["Location"] == reverse("accounts:account-home")


def test_login_is_blocked_until_email_is_verified():
    user = User.objects.create_user(
        email="pending@bam.de",
        password="HighlySecurePass123!!",
        first_name="Pending",
        last_name="User",
    )
    client = Client()

    response = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "HighlySecurePass123!!"},
    )

    assert response.status_code == 200
    assert settings.ACCOUNT_REQUIRE_ADMIN_APPROVAL is True
    assert b"Verify your email address before signing in." in response.content


def test_verified_user_waits_for_admin_approval_by_default():
    user = User.objects.create_user(
        email="moderated@bam.de",
        password="HighlySecurePass123!!",
        first_name="Moderated",
        last_name="User",
    )
    client = Client()

    verify_response = client.get(build_verification_path(user))

    user.refresh_from_db()
    assert verify_response.status_code == 200
    assert user.is_email_verified is True
    assert user.is_approved is False
    assert b"waiting for approval" in verify_response.content

    login_response = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "HighlySecurePass123!!"},
    )

    assert login_response.status_code == 200
    assert b"waiting for administrator approval" in login_response.content

    user.mark_approved()
    login_after_approval = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "HighlySecurePass123!!"},
    )

    assert login_after_approval.status_code == 302
    assert login_after_approval.headers["Location"] == reverse("accounts:account-home")


def test_resend_verification_email_is_generic_but_sends_for_pending_users():
    user = User.objects.create_user(
        email="resend@bam.de",
        password="HighlySecurePass123!!",
        first_name="Resend",
        last_name="User",
    )
    client = Client()
    mail.outbox.clear()

    response = client.post(
        reverse("accounts:resend-verification"),
        {"email": user.email},
        follow=True,
    )

    assert response.status_code == 200
    assert len(mail.outbox) == 1
    assert b"fresh verification email has been sent" in response.content


def test_deactivated_user_cannot_sign_in():
    user = User.objects.create_user(
        email="inactive@bam.de",
        password="HighlySecurePass123!!",
        first_name="Inactive",
        last_name="User",
    )
    user.mark_email_verified()
    user.mark_approved()
    user.deactivate()
    client = Client()

    response = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "HighlySecurePass123!!"},
    )

    assert response.status_code == 200
    assert b"This account has been disabled." in response.content
