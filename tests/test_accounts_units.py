from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.test import RequestFactory, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.admin import UserAdmin
from apps.accounts.forms import (
    EmailAuthenticationForm,
    RegistrationForm,
    ResendVerificationEmailForm,
)
from apps.accounts.models import User
from apps.accounts.services import build_email_verification_url, send_verification_email
from apps.accounts.views import VerifyEmailView
from apps.directory.models import AuditEvent

pytestmark = pytest.mark.django_db
UserModel = get_user_model()


def test_registration_form_normalizes_email_for_valid_bam_account():
    form = RegistrationForm(
        data={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "Ada@BAM.DE",
            "password1": "HighlySecurePass123!!",
            "password2": "HighlySecurePass123!!",
        }
    )

    assert form.is_valid()
    assert form.cleaned_data["email"] == "ada@bam.de"


def test_registration_form_rejects_duplicate_email_case_insensitively():
    UserModel.objects.create_user(
        email="existing@bam.de",
        password="HighlySecurePass123!!",
    )
    form = RegistrationForm(
        data={
            "first_name": "Existing",
            "last_name": "User",
            "email": "Existing@Bam.de",
            "password1": "HighlySecurePass123!!",
            "password2": "HighlySecurePass123!!",
        }
    )

    assert not form.is_valid()
    assert form.errors["email"] == ["An account with this email address already exists."]


def test_resend_verification_email_form_lowercases_email():
    form = ResendVerificationEmailForm(data={"email": "MixedCase@BAM.DE"})

    assert form.is_valid()
    assert form.cleaned_data["email"] == "mixedcase@bam.de"


def test_email_authentication_form_surfaces_inactive_account_message():
    user = UserModel.objects.create_user(
        email="inactive@bam.de",
        password="HighlySecurePass123!!",
    )
    user.deactivate(save=False)
    user.save(update_fields=["is_active", "deactivated_at", "deactivated_by", "updated_at"])

    form = EmailAuthenticationForm(
        request=RequestFactory().post(reverse("accounts:login")),
        data={"username": "inactive@bam.de", "password": "HighlySecurePass123!!"},
    )

    assert not form.is_valid()
    assert form.non_field_errors() == [
        "This account has been disabled. Contact an administrator for help."
    ]


def test_email_authentication_form_requires_verified_users():
    user = UserModel.objects.create_user(
        email="pending@bam.de",
        password="HighlySecurePass123!!",
    )
    form = EmailAuthenticationForm()

    with pytest.raises(ValidationError, match="Verify your email address before signing in."):
        form.confirm_login_allowed(user)


def test_email_authentication_form_requires_admin_approval_by_default():
    user = UserModel.objects.create_user(
        email="unapproved@bam.de",
        password="HighlySecurePass123!!",
    )
    user.mark_email_verified()
    form = EmailAuthenticationForm()

    with pytest.raises(
        ValidationError,
        match="Your account is waiting for administrator approval.",
    ):
        form.confirm_login_allowed(user)


@override_settings(ACCOUNT_REQUIRE_ADMIN_APPROVAL=False)
def test_email_authentication_form_allows_verified_user_without_approval_when_disabled():
    user = UserModel.objects.create_user(
        email="verified@bam.de",
        password="HighlySecurePass123!!",
    )
    user.mark_email_verified()
    form = EmailAuthenticationForm()

    form.confirm_login_allowed(user)


def test_build_email_verification_url_returns_absolute_verification_link():
    user = UserModel.objects.create_user(
        email="person@bam.de",
        password="HighlySecurePass123!!",
    )
    request = RequestFactory().get("/")

    url = build_email_verification_url(user, request)

    assert url.startswith("http://testserver")
    assert "/accounts/verify/" in url


def test_send_verification_email_renders_templates_and_sends_mail():
    user = UserModel.objects.create_user(
        email="notify@bam.de",
        password="HighlySecurePass123!!",
    )
    request = RequestFactory().get("/")

    with (
        patch(
            "apps.accounts.services.build_email_verification_url",
            return_value="http://test/verify",
        ) as build_url,
        patch(
            "apps.accounts.services.render_to_string",
            side_effect=["Verify your BAMatlas account\n", "Email body"],
        ) as render,
        patch("apps.accounts.services.send_mail") as send_mail_mock,
    ):
        send_verification_email(user, request)

    build_url.assert_called_once_with(user, request)
    assert render.call_count == 2
    send_mail_mock.assert_called_once_with(
        "Verify your BAMatlas account",
        "Email body",
        "noreply@bamatlas.local",
        [user.email],
    )


def test_create_superuser_sets_verification_and_approval_timestamps():
    now = timezone.now()

    with patch("apps.accounts.managers.timezone.now", return_value=now):
        user = UserModel.objects.create_superuser(
            email="admin@bam.de",
            password="HighlySecurePass123!!",
        )

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_email_verified is True
    assert user.is_approved is True
    assert user.email_verified_at == now
    assert user.approved_at == now


def test_create_superuser_rejects_invalid_staff_flag():
    with pytest.raises(ValueError, match="Superuser must have is_staff=True."):
        UserModel.objects.create_superuser(
            email="badstaff@bam.de",
            password="HighlySecurePass123!!",
            is_staff=False,
        )


def test_create_superuser_rejects_invalid_superuser_flag():
    with pytest.raises(ValueError, match="Superuser must have is_superuser=True."):
        UserModel.objects.create_superuser(
            email="badsuperuser@bam.de",
            password="HighlySecurePass123!!",
            is_superuser=False,
        )


def test_mark_email_verified_is_idempotent():
    user = UserModel.objects.create_user(
        email="idempotent-email@bam.de",
        password="HighlySecurePass123!!",
    )
    first_time = timezone.now()
    second_time = first_time + timedelta(days=1)

    with patch("apps.accounts.models.timezone.now", side_effect=[first_time, second_time]):
        user.mark_email_verified(save=False)
        user.mark_email_verified(save=False)

    assert user.is_email_verified is True
    assert user.email_verified_at == first_time


def test_mark_approved_is_idempotent():
    user = UserModel.objects.create_user(
        email="idempotent-approval@bam.de",
        password="HighlySecurePass123!!",
    )
    first_time = timezone.now()
    second_time = first_time + timedelta(days=1)

    with patch("apps.accounts.models.timezone.now", side_effect=[first_time, second_time]):
        user.mark_approved(save=False)
        user.mark_approved(save=False)

    assert user.is_approved is True
    assert user.approved_at == first_time


def test_deactivate_and_reactivate_update_user_state():
    moderator = UserModel.objects.create_superuser(
        email="moderator@bam.de",
        password="HighlySecurePass123!!",
    )
    user = UserModel.objects.create_user(
        email="toggle@bam.de",
        password="HighlySecurePass123!!",
    )

    user.deactivate(by_user=moderator, save=False)
    assert user.is_active is False
    assert user.deactivated_by == moderator
    assert user.deactivated_at is not None

    user.reactivate(save=False)
    assert user.is_active is True
    assert user.deactivated_by is None
    assert user.deactivated_at is None


def test_verify_email_view_returns_invalid_state_for_unknown_uid():
    view = VerifyEmailView()
    view.request = RequestFactory().get("/")
    view.args = ()
    view.kwargs = {"uidb64": "invalid", "token": "token"}

    context = view.get_context_data()

    assert context["verification_state"] == "invalid"


def test_verify_email_view_marks_user_verified_for_valid_token():
    user = UserModel.objects.create_user(
        email="verifyme@bam.de",
        password="HighlySecurePass123!!",
    )
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    view = VerifyEmailView()
    view.request = RequestFactory().get("/")
    view.args = ()
    view.kwargs = {"uidb64": uid, "token": token}

    context = view.get_context_data()

    user.refresh_from_db()
    assert context["verification_state"] == "pending-approval"
    assert user.is_email_verified is True


def test_user_admin_actions_update_users_and_write_audit_events():
    request = RequestFactory().post("/admin/accounts/user/")
    moderator = UserModel.objects.create_superuser(
        email="admin-action@bam.de",
        password="HighlySecurePass123!!",
    )
    pending_user = UserModel.objects.create_user(
        email="pending-action@bam.de",
        password="HighlySecurePass123!!",
    )
    inactive_user = UserModel.objects.create_user(
        email="inactive-action@bam.de",
        password="HighlySecurePass123!!",
    )
    inactive_user.deactivate(save=True)
    request.user = moderator

    admin_instance = UserAdmin(User, Mock())
    admin_instance.message_user = Mock()

    admin_instance.approve_selected_users(request, UserModel.objects.filter(pk=pending_user.pk))
    pending_user.refresh_from_db()
    assert pending_user.is_approved is True
    assert AuditEvent.objects.filter(
        actor=moderator,
        target_user=pending_user,
        action=AuditEvent.Action.USER_APPROVED,
    ).exists()

    admin_instance.deactivate_selected_users(
        request,
        UserModel.objects.filter(pk__in=[moderator.pk, pending_user.pk]),
    )
    pending_user.refresh_from_db()
    moderator.refresh_from_db()
    assert pending_user.is_active is False
    assert moderator.is_active is True
    assert AuditEvent.objects.filter(
        actor=moderator,
        target_user=pending_user,
        action=AuditEvent.Action.USER_DEACTIVATED,
    ).exists()

    admin_instance.reactivate_selected_users(request, UserModel.objects.filter(pk=inactive_user.pk))
    inactive_user.refresh_from_db()
    assert inactive_user.is_active is True
    assert AuditEvent.objects.filter(
        actor=moderator,
        target_user=inactive_user,
        action=AuditEvent.Action.USER_REACTIVATED,
    ).exists()
