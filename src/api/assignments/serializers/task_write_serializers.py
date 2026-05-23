from rest_framework import serializers

from src.apps.assignments.models import Task


class TaskWriteSerializer(serializers.ModelSerializer):
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
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
            "created_by": {"required": False},
        }
