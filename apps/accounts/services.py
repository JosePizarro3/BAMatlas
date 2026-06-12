from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def build_email_verification_url(user, request):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return request.build_absolute_uri(reverse("accounts:verify-email", args=[uid, token]))


def send_verification_email(user, request):
    verification_url = build_email_verification_url(user, request)
    context = {
        "user": user,
        "verification_url": verification_url,
        "require_admin_approval": settings.ACCOUNT_REQUIRE_ADMIN_APPROVAL,
    }
    subject = render_to_string("accounts/emails/verify_subject.txt", context).strip()
    body = render_to_string("accounts/emails/verify_body.txt", context)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
