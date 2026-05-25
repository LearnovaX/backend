from rest_framework import serializers

from src.api.courses.serializers import CourseGroupReadSerializer
from src.api.users.serializers import AllUsersSerializerLight
from src.apps.courses.models.groups import CourseEnrollment


class CourseEnrollmentReadSerializer(serializers.ModelSerializer):
    user = AllUsersSerializerLight(read_only=True)
    group = CourseGroupReadSerializer(read_only=True)

    class Meta:
        model = CourseEnrollment
        fields = ["id", "user", "group", "role", "enrolled_date"]
