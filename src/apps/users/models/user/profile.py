from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q

from src.apps.common.utils.files import unique_image_path
from src.apps.common.utils.validators import validate_image_size


class UserProfile(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="profile")
    middle_name = models.CharField(max_length=120, null=True, blank=True)
    interface_language = models.CharField(max_length=10, default="en", null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC+5", null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    profile_edit_blocked = models.BooleanField(default=False)
    deactivation_time = models.DateTimeField(null=True, blank=True)
    days_to_delete_after_deactivation = models.PositiveIntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    company = models.CharField(max_length=100, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    profile_photo = models.ImageField(
        null=True,
        blank=True,
        upload_to=unique_image_path,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"]),
            validate_image_size,
        ],
    )

    def __str__(self):
        return f"profile for {self.user.first_name} - {self.user.last_name} - {self.user.email}"

    class Meta:
        db_table = "Users Profile"
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        constraints = [
            models.UniqueConstraint(
                fields=["phone_number"],
                name="unique_phone_number_when_set",
                condition=~Q(phone_number=None),
            )
        ]
