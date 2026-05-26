from rest_framework import serializers

from src.apps.courses.models import Course


class CourseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "description",
            "author",
            "free_order",
            "category",
            "image",
            "deadline_to_finish_course",
            "block_course_after_deadline",
            "is_certificated",
            "created_at",
            "updated_at",
            "allow_teachers_to_manage_tasks",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
        }
