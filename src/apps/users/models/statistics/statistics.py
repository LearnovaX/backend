from django.db import models
from django.utils import timezone


class DailyUserStatistics(models.Model):
    """
    Daily snapshot of user statistics for historical tracking and charts.
    This table should be populated daily via a cron job or management command.
    """

    date = models.DateField(unique=True, db_index=True)

    # Core user counts
    total_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    inactive_users = models.PositiveIntegerField(default=0)
    authorized_users = models.PositiveIntegerField(default=0)
    not_authorized_users = models.PositiveIntegerField(default=0)

    # Growth metrics (daily new users)
    new_users_today = models.PositiveIntegerField(default=0)
    deactivated_users_today = models.PositiveIntegerField(default=0)

    # Profile completeness
    complete_profile_users = models.PositiveIntegerField(default=0)

    # Role distribution (stored as JSON for flexibility)
    role_distribution = models.JSONField(default=dict)

    # Enrollment statistics
    total_enrollments = models.PositiveIntegerField(default=0)
    active_enrollments = models.PositiveIntegerField(default=0)

    # Calculated rates (stored for performance)
    email_verified_rate = models.FloatField(default=0.0)
    profile_completion_rate = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Daily User Statistics"
        verbose_name = "Daily User Statistics"
        verbose_name_plural = "Daily User Statistics"
        ordering = ["-date"]

    def __str__(self):
        return f"Statistics for {self.date} - {self.total_users} total users"

    @classmethod
    def generate_daily_snapshot(cls, target_date=None):
        """
        Generate a daily snapshot of user statistics.
        This should be called daily via a cron job or management command.
        """
        from src.apps.courses.models import CourseEnrollment
        from src.apps.users.models import Role, User

        if target_date is None:
            target_date = timezone.now().date()

        # Calculate all statistics for the target date
        # Note: We calculate stats as of the END of the target date
        end_of_day = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.max.time())
        )

        # Core user counts (as of end of target date)
        total_users = User.objects.filter(date_joined__lte=end_of_day).count()
        active_users = User.objects.filter(date_joined__lte=end_of_day, is_active=True).count()
        inactive_users = total_users - active_users

        authorized_users = User.objects.filter(
            date_joined__lte=end_of_day,
            is_active=True,
            must_set_password=False,
            email_verified=True,
        ).count()
        not_authorized_users = total_users - authorized_users

        # Daily growth metrics
        start_of_day = timezone.make_aware(
            timezone.datetime.combine(target_date, timezone.datetime.min.time())
        )
        new_users_today = User.objects.filter(date_joined__range=[start_of_day, end_of_day]).count()

        # Users deactivated today (check profile deactivation_time)
        deactivated_users_today = User.objects.filter(
            profile__deactivation_time__range=[start_of_day, end_of_day]
        ).count()

        # Profile completeness
        complete_profile_users = User.objects.filter(
            date_joined__lte=end_of_day,
            profile__phone_number__isnull=False,
            profile__profile_photo__isnull=False,
        ).count()

        # Role distribution
        role_distribution = {}
        for role_code, role_name in Role.choices:
            count = User.objects.filter(date_joined__lte=end_of_day, role=role_code).count()
            role_distribution[role_name] = count

        # Enrollment statistics
        total_enrollments = CourseEnrollment.objects.filter(enrolled_date__lte=end_of_day).count()

        active_enrollments = CourseEnrollment.objects.filter(
            enrolled_date__lte=end_of_day, user__is_active=True
        ).count()

        # Calculate rates
        profile_completion_rate = (
            (complete_profile_users / total_users * 100) if total_users > 0 else 0
        )

        # Create or update the record
        stats, created = cls.objects.update_or_create(
            date=target_date,
            defaults={
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": inactive_users,
                "authorized_users": authorized_users,
                "not_authorized_users": not_authorized_users,
                "new_users_today": new_users_today,
                "deactivated_users_today": deactivated_users_today,
                "complete_profile_users": complete_profile_users,
                "role_distribution": role_distribution,
                "total_enrollments": total_enrollments,
                "active_enrollments": active_enrollments,
                "profile_completion_rate": profile_completion_rate,
            },
        )

        return stats
