import os

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
ACCOUNT_ALLOWED_EMAIL_DOMAINS = [
    domain.strip()
    for domain in os.environ.get("ACCOUNT_ALLOWED_EMAIL_DOMAINS", "bam.de").split(",")
    if domain.strip()
]
ACCOUNT_REQUIRE_ADMIN_APPROVAL = (
    os.environ.get("ACCOUNT_REQUIRE_ADMIN_APPROVAL", "true").lower()
    in {"1", "true", "yes", "on"}
)

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
