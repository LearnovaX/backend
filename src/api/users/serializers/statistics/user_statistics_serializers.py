from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from src.apps.courses.models import CourseEnrollment
from src.apps.users.models import User


class StatisticsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    enrolled_users = serializers.IntegerField()
    authorized_users = serializers.IntegerField()
    users_last_day = serializers.IntegerField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        total_users = data["total_users"]

        if total_users > 0:
            data["email_verified_rate"] = (data["authorized_users"] / total_users) * 100
        else:
            data["email_verified_rate"] = 0

        return data

    @staticmethod
    def calculate_statistics():
        today = timezone.now()

        total_users = User.objects.count()
        enrolled_users = CourseEnrollment.objects.values("user").distinct().count()
        authorized_users = User.authorized_users.count()
        users_last_day = User.objects.filter(date_joined__gte=today - timedelta(days=1)).count()

        return {
            "total_users": total_users,
            "enrolled_users": enrolled_users,
            "authorized_users": authorized_users,
            "users_last_day": users_last_day,
        }
