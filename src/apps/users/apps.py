from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.apps.users"

    def ready(self):
        from .signals import add_superuser_to_admins_group, create_user_profile  # noqa: F401
