from rest_framework import serializers

from src.api.grades.serializers import GradeReadSerializer
from src.api.submissions.serializers import AnswerFileSerializer
from src.api.users.serializers import AllUsersSerializerLight
from src.apps.submissions.models import Answer


class AnswerReadSerializer(serializers.ModelSerializer):
    task = serializers.SerializerMethodField()
    user = AllUsersSerializerLight(read_only=True)
    files = AnswerFileSerializer(many=True, read_only=True)
    files_count = serializers.SerializerMethodField()
    grade = GradeReadSerializer(read_only=True)

    feedback = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = [
            "id",
            "task",
            "user",
            "description",
            "status",
            "plagiarism_status",
            "analyzed_at",
            "grade",  # New field
            "feedback",  # Backward compatibility
            "created_at",
            "updated_at",
            "files",
            "files_count",
        ]

    def get_files_count(self, instance: Answer):
        return instance.files.count()

    def get_feedback(self, instance: Answer):
        """Backward compatibility - return grade data as feedback format"""
        if hasattr(instance, "grade") and instance.grade and instance.grade.graded_by:
            return {
                "id": instance.grade.id,
                "feedback_text": instance.grade.feedback_text,
                "given_by": {
                    "id": instance.grade.graded_by.id,
                    "first_name": instance.grade.graded_by.first_name,
                    "last_name": instance.grade.graded_by.last_name,
                    "email": instance.grade.graded_by.email,
                },
                "created_at": instance.grade.created_at,
                "updated_at": instance.grade.updated_at,
            }
        return None

    def get_task(self, obj: Answer):
        from src.api.assignments.serializers.task_read_serializer import TaskReadSerializer

        return TaskReadSerializer(obj.task, context=self.context).data
