from rest_framework import serializers

from src.apps.courses.models.groups import CourseEnrollment


class CourseEnrollmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseEnrollment
        fields = ["user", "course", "group", "role", "enrolled_date"]
