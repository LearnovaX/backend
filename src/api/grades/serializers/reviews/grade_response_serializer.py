from rest_framework import serializers

from src.apps.grades.models import Grade


class GradeResponseSerializer(serializers.ModelSerializer):
    """Lightweight serializer for API responses"""

    percentage = serializers.SerializerMethodField()
    letter_grade = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [
            "id",
            "score",
            "max_score",
            "percentage",
            "letter_grade",
            "feedback_text",
            "updated_at",
        ]

    def get_percentage(self, obj):
        return obj.percentage

    def get_letter_grade(self, obj):
        return obj.letter_grade
