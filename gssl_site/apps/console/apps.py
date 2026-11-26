from django.apps import AppConfig


class ConsoleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.console"
    label = "console"
    verbose_name = "Console"

    def ready(self):
        # Importing the module list is what fills the registry, and so the
        # navigation and the URL patterns.
        from . import modules  # noqa: F401
