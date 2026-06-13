from django.apps import AppConfig


class DirectoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.directory"
    label = "directory"
    verbose_name = "Directory"

    def ready(self) -> None:
        from . import signals  # noqa: F401
