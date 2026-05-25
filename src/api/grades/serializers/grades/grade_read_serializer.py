from rest_framework import serializers

from src.api.users.serializers import AllUsersSerializerLight
from src.apps.grades.models import Grade


class GradeReadSerializer(serializers.ModelSerializer):
    graded_by = AllUsersSerializerLight(read_only=True)
    percentage = serializers.SerializerMethodField()
    letter_grade = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [
            "id",
            "score",
            "max_score",
            "percentage",
            "feedback_text",
            "letter_grade",
            "graded_by",
            "created_at",
            "updated_at",
        ]

    def get_percentage(self, obj: Grade) -> int:
        return obj.percentage

    def get_letter_grade(self, obj: Grade) -> str:
        return obj.letter_grade
