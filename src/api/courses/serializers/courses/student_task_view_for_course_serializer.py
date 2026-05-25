from rest_framework import serializers

from src.api.submissions.serializers import PublicAnswerReadSerializer
from src.apps.assignments.models import Task


class StudentTaskViewForCourseSerializer(serializers.ModelSerializer):
    answer = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "number",
            "name",
            "description",
            "video",
            "image",
            "file",
            "course",
            "allow_resubmitting_task",
            "enable_context_menu_for_students",
            "created_at",
            "updated_at",
            "answer",
        ]

    def get_answer(self, obj: Task):
        request = self.context.get("request")
        answer = (
            obj.student_answer[0] if hasattr(obj, "student_answer") and obj.student_answer else None
        )
        return (
            PublicAnswerReadSerializer(answer, context={"request": request}).data
            if answer
            else None
        )
