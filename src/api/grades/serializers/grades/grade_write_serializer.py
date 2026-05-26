from rest_framework import serializers

from src.apps.grades.models import Grade


class GradeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = ["answer", "score", "max_score", "feedback_text"]

    def validate(self, attrs):
        score = attrs.get("score")
        max_score = attrs.get("max_score", 100)

        if score is not None and score > max_score:
            raise serializers.ValidationError("Score cannot exceed maximum score")

        # At least one of score or feedback_text should be provided
        if not score and not attrs.get("feedback_text", "").strip():
            raise serializers.ValidationError("Either score or feedback text must be provided")

        return attrs

    def validate_feedback_text(self, value):
        """Ensure feedback text is properly trimmed"""
        return value.strip() if value else ""
