import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from src.apps.common.models import BaseModel
from src.apps.common.validators import validate_days_of_week
from src.apps.courses.models.courses import Course
from src.apps.users.models import User

from .manager import CourseGroupManager


class CourseGroup(BaseModel):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="groups"
    )  # TODO I'll remove this

    students_limit = models.PositiveIntegerField(null=True, blank=True)
    days_of_week = models.JSONField(
        default=list,
        help_text="List of weekday numbers (0=Monday)",
        blank=True,
        validators=[validate_days_of_week],
    )
    self_registration = models.BooleanField(default=False)
    registration_token = models.CharField(max_length=128, unique=True, null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    token_validity_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of hours the registration token should be valid. "
        "Leave empty for no expiration.",
    )
    token_validity_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of days the registration token should be valid. "
        "Leave empty for no expiration.",
    )
    is_active = models.BooleanField(default=True)

    objects = CourseGroupManager()

    def generate_unique_token(self, hours_valid=None, days_valid=None):
        """Generate a unique registration token with optional expiration"""
        self.registration_token = secrets.token_urlsafe(64)

        hours = hours_valid if hours_valid is not None else self.token_validity_hours
        days = days_valid if days_valid is not None else self.token_validity_days

        if (days and days > 0) or (hours and hours > 0):
            self.token_expires_at = timezone.now() + timedelta(
                days=days or 0,
                hours=hours or 0,
            )
        else:
            self.token_expires_at = None  # No expiration

        self.save()

    def invalidate_token(self):
        """Invalidate the current registration token"""
        self.registration_token = None
        self.token_expires_at = None
        self.save()

    def is_token_expired(self):
        """Check if the registration token is expired"""
        if not self.token_expires_at:
            return False
        return self.token_expires_at < timezone.now()

    @property
    def registration_link(self):
        if self.self_registration:
            return f"{settings.ENROL_LINK_URL}{self.registration_token}"
        return ""

    @property
    def teachers(self):
        return (
            User.objects.select_related("profile")
            .filter(enrollments__group=self, enrollments__role="teacher")
            .distinct()
        )

    def __str__(self):
        return f"'{self.name}' group in '{self.course.name}' course"

    class Meta:
        db_table = "Course Groups"
        verbose_name = "Course Group"
        verbose_name_plural = "Course Groups"
