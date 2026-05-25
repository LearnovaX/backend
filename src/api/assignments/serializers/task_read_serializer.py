from rest_framework import serializers

from src.apps.assignments.models import Task


class TaskReadSerializer(serializers.ModelSerializer):
    course = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "name",
            "number",
            "description",
            "video",
            "image",
            "file",
            "course",
            "allow_resubmitting_task",
            "enable_context_menu_for_students",
            "created_by",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
        }

    def get_course(self, obj):
        from src.api.courses.serializers.courses.course_read_light_serializer import (
            CourseReadLightWithRoleSerializer,
        )

        return CourseReadLightWithRoleSerializer(obj.course, context=self.context).data
