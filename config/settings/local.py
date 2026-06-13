from .base import *  # noqa: F403

DEBUG = env_bool("DJANGO_DEBUG", True)  # noqa: F405
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-local-dev-key")  # noqa: F405
ALLOWED_HOSTS = env_list(  # noqa: F405
    "DJANGO_ALLOWED_HOSTS",
    ["127.0.0.1", "localhost", "testserver"],
)
