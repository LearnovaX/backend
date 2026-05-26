from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.functional import cached_property


class Role(models.TextChoices):
    STUDENT = "student", "Student"
    TEACHER = "teacher", "Teacher"
    # ASSISTANT = "assistant", "Assistant"
    # MANAGER = "manager", "Manager"
    ADMIN = "admin", "Admin"


from .managers import AuthorizedUsersManager  # noqa E402
from .managers import CustomUserManager  # noqa E402
from .managers import DeactivatedUsersManager  # noqa E402
from .managers import NotAuthorizedUsersManager  # noqa E402; noqa E402


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    google_id = models.CharField(max_length=50, unique=True, null=True, blank=True)

    email_verified = models.BooleanField(default=False)
    must_set_password = models.BooleanField(default=True)
    mfa_enabled = models.BooleanField(default=False)

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    is_deleted = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name"]

    objects = CustomUserManager()
    authorized_users = AuthorizedUsersManager()
    not_authorized_users = NotAuthorizedUsersManager()
    deactivated_users = DeactivatedUsersManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"

    @cached_property
    def cached_group_names(self):
        return set(self.groups.values_list("name", flat=True))

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        db_table = "Users"
        indexes = [
            models.Index(fields=["is_active", "must_set_password", "email_verified"]),
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["email", "first_name", "last_name"]),
        ]
