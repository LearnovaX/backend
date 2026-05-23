from difflib import HtmlDiff
from html import escape

from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from src.api.plagiarism.permissions import IsTeacherOrAdmin, is_admin
from src.api.plagiarism.serializers import (
    PlagiarismReportListSerializer,
    PlagiarismReviewSerializer,
)
from src.apps.courses.models import CourseEnrollment
from src.apps.plagiarism.models import PlagiarismReport
from src.apps.submissions.models import Answer


class PlagiarismReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlagiarismReportListSerializer
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        queryset = (
            PlagiarismReport.objects.select_related(
                "submission_a__user",
                "submission_a__task__course",
                "submission_b__user",
                "submission_b__task__course",
                "reviewed_by",
            )
            .filter(is_deleted=False)
            .order_by("-similarity_score", "-created_at")
        )
        queryset = _scope_reports_to_user(queryset, self.request.user)

        review_status = self.request.query_params.get("review_status")
        if review_status:
            queryset = queryset.filter(review_status=review_status)

        task_id = self.request.query_params.get("task_id")
        if task_id:
            queryset = queryset.filter(submission_a__task_id=task_id)

        return queryset

    @action(detail=True, methods=["get"], url_path="comparison")
    def comparison(self, request, pk=None):
        report = self.get_object()
        text_a = report.submission_a.extracted_text or ""
        text_b = report.submission_b.extracted_text or ""
        diff_html = HtmlDiff(wrapcolumn=100).make_table(
            escape(text_a).splitlines(),
            escape(text_b).splitlines(),
            fromdesc=escape(_student_label(report.submission_a)),
            todesc=escape(_student_label(report.submission_b)),
            context=True,
            numlines=3,
        )

        return Response(
            {
                "report": self.get_serializer(report).data,
                "diff_html": diff_html,
                "includes_ocr": _answer_may_include_ocr(report.submission_a)
                or _answer_may_include_ocr(report.submission_b),
            }
        )

    @action(detail=True, methods=["patch"], url_path="review")
    def review(self, request, pk=None):
        report = self.get_object()
        serializer = PlagiarismReviewSerializer(report, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        review_status = serializer.validated_data.get("review_status", report.review_status)
        review_note = serializer.validated_data.get("review_note", report.review_note)
        report.mark_reviewed(status=review_status, reviewer=request.user, note=review_note)
        return Response(self.get_serializer(report).data, status=status.HTTP_200_OK)


class PlagiarismDashboardView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        reports = _scope_reports_to_user(PlagiarismReport.objects.filter(is_deleted=False), request.user)

        assignments = (
            reports.values(
                "submission_a__task_id",
                "submission_a__task__name",
                "submission_a__task__course__name",
            )
            .annotate(
                suspicious_reports=Count("id", filter=Q(flagged=True)),
                total_reports=Count("id"),
                highest_similarity=Max("similarity_score"),
            )
            .order_by("-suspicious_reports", "-highest_similarity")
        )

        data = {
            "assignments": [
                {
                    "task_id": row["submission_a__task_id"],
                    "assignment_name": row["submission_a__task__name"],
                    "course_name": row["submission_a__task__course__name"],
                    "suspicious_reports": row["suspicious_reports"],
                    "total_reports": row["total_reports"],
                    "highest_similarity": row["highest_similarity"] or 0,
                    "highest_similarity_percent": round((row["highest_similarity"] or 0) * 100),
                }
                for row in assignments
            ],
            "summary": {
                "total_reports": reports.count(),
                "flagged_reports": reports.filter(flagged=True).count(),
                "pending_review": reports.filter(
                    review_status=PlagiarismReport.ReviewStatus.pending_review
                ).count(),
            },
        }

        if is_admin(request.user):
            today = timezone.localdate()
            data["admin_metrics"] = {
                "submissions_analyzed_today": Answer.objects.filter(
                    plagiarism_status=Answer.PlagiarismStatus.analyzed,
                    analyzed_at__date=today,
                ).count(),
                "failed_processing_count": Answer.objects.filter(
                    plagiarism_status=Answer.PlagiarismStatus.failed
                ).count(),
                "flagged_reports_count": PlagiarismReport.objects.filter(flagged=True).count(),
            }

        return Response(data)


def _scope_reports_to_user(queryset, user):
    if is_admin(user):
        return queryset

    teacher_group_ids = CourseEnrollment.objects.filter(
        user=user,
        role="teacher",
    ).values_list("group_id", flat=True)
    student_ids = CourseEnrollment.objects.filter(
        group_id__in=teacher_group_ids,
        role="student",
    ).values_list("user_id", flat=True)

    return queryset.filter(
        submission_a__user_id__in=student_ids,
        submission_b__user_id__in=student_ids,
        submission_a__task__course__enrollments__user=user,
        submission_a__task__course__enrollments__role="teacher",
    ).distinct()


def _student_label(answer: Answer) -> str:
    return f"{answer.user.get_full_name() or answer.user.email} - {answer.task.name}"


def _answer_may_include_ocr(answer: Answer) -> bool:
    return answer.files.filter(content_type__startswith="image/").exists()
