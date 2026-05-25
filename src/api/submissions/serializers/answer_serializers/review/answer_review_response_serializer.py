from rest_framework import serializers

from src.api.users.serializers import UserSerializer
from src.apps.submissions.models import Answer


class AnswerReviewResponseSerializer(serializers.ModelSerializer):
    """Lightweight serializer for review endpoint responses"""

    feedback_text = serializers.SerializerMethodField()
    grade_info = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = ["id", "status", "status_display", "feedback_text", "grade_info", "updated_at"]

    def get_feedback_text(self, obj):
        return obj.grade.feedback_text if hasattr(obj, "grade") and obj.grade else None

    def get_grade_info(self, obj):
        if hasattr(obj, "grade") and obj.grade:
            user = self.context.get("request").user
            data = {
                "score": obj.grade.score,
                "max_score": obj.grade.max_score,
                "percentage": obj.grade.percentage,
                "letter_grade": obj.grade.letter_grade,
            }
            if user.groups.filter(name__in=["Teachers", "Admins"]).exists():
                if obj.grade.graded_by:
                    data["graded_by"] = UserSerializer(obj.grade.graded_by).data
            return data
        return None

    def get_status_display(self, obj):
        return dict(Answer.Status.choices).get(obj.status, obj.status)
