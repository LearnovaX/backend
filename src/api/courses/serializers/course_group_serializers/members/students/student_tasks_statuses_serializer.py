from rest_framework import serializers

from src.apps.assignments.models import Task


class StudentTasksStatusSerializer(serializers.Serializer):
    task_id = serializers.IntegerField(source="pk")
    status = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()

    def get_status(self, obj: Task) -> str | None:
        answers = getattr(obj, "user_answers", None)
        if answers:
            return answers[0].status  # unique_together ensures at most one
        return None

    def get_grade(self, obj: Task) -> int | None:
        answers = getattr(obj, "user_answers", None)
        if not answers:
            return None
        answer = answers[0]
        # grade is reverse OneToOne; prefetch_related('grade') populated it
        grade = getattr(answer, "grade", None)
        return getattr(grade, "score", None)
