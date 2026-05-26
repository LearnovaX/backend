from rest_framework import serializers

from src.apps.courses.models import CourseGroup


class CourseGroupListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseGroup
        fields = ["id", "name"]
