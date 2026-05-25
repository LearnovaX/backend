from django.contrib.auth.base_user import BaseUserManager
from django.db.models import Q


class NotAuthorizedUsersManager(BaseUserManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(Q(is_active=True) & (Q(must_set_password=True) | Q(email_verified=False)))
        )

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)
