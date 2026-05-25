from rest_framework import serializers

from src.apps.plagiarism.models import PlagiarismReport


class SubmissionSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    student_name = serializers.CharField()
    student_email = serializers.EmailField()
    task_id = serializers.IntegerField()
    task_name = serializers.CharField()
    course_name = serializers.CharField()
    plagiarism_status = serializers.CharField()
    analyzed_at = serializers.DateTimeField(allow_null=True)


class PlagiarismReportListSerializer(serializers.ModelSerializer):
    submission_a = serializers.SerializerMethodField()
    submission_b = serializers.SerializerMethodField()
    assignment_name = serializers.CharField(source="submission_a.task.name", read_only=True)
    course_name = serializers.CharField(source="submission_a.task.course.name", read_only=True)
    similarity_percent = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PlagiarismReport
        fields = [
            "id",
            "submission_a",
            "submission_b",
            "assignment_name",
            "course_name",
            "similarity_score",
            "similarity_percent",
            "flagged",
            "review_status",
            "review_note",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
        ]

    def get_similarity_percent(self, obj: PlagiarismReport) -> int:
        return round(obj.similarity_score * 100)

    def get_submission_a(self, obj: PlagiarismReport) -> dict:
        return _submission_summary(obj.submission_a)

    def get_submission_b(self, obj: PlagiarismReport) -> dict:
        return _submission_summary(obj.submission_b)

    def get_reviewed_by_name(self, obj: PlagiarismReport) -> str | None:
        if not obj.reviewed_by:
            return None
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.email


class PlagiarismReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlagiarismReport
        fields = ["review_status", "review_note"]

    def validate_review_status(self, value: str) -> str:
        allowed = {choice[0] for choice in PlagiarismReport.ReviewStatus.choices}
        if value not in allowed:
            raise serializers.ValidationError("Invalid review status.")
        return value


def _submission_summary(answer) -> dict:
    user = answer.user
    return {
        "id": answer.id,
        "student_name": user.get_full_name() or user.email,
        "student_email": user.email,
        "task_id": answer.task_id,
        "task_name": answer.task.name,
        "course_name": answer.task.course.name,
        "plagiarism_status": answer.plagiarism_status,
        "analyzed_at": answer.analyzed_at,
    }
