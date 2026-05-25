from django.contrib.auth.models import Group
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from src.api.submissions.serializers import (
    AnswerFileSerializer,
    AnswerFileUploadSerializer,
    AnswerReadSerializer,
    AnswerReviewSerializer,
    AnswerWriteSerializer,
)
from src.apps.common.permissions import IsAdminOrTeacher, IsEnrolledToCourse
from src.apps.common.permissions.answers.answer_permissions import IsOwnerOfAnswer
from src.apps.courses.models import CourseEnrollment, CourseGroup
from src.apps.submissions.models import Answer, AnswerFile


@extend_schema(tags=["Answers"])
class AnswerModelViewSet(ModelViewSet):
    queryset = Answer.objects.select_related("task", "user").prefetch_related("files", "grade")
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update"]:
            user = self.request.user
            group, _ = Group.objects.get_or_create(name="Students")
            if user.groups.filter(name=group.name).exists():
                return [IsEnrolledToCourse()]
            return [IsAdminOrTeacher()]
        elif self.action in ["teacher_review_answers", "check"]:
            return [IsAdminOrTeacher()]
        elif self.action in ["files"]:
            return [IsOwnerOfAnswer()]
        elif self.action in ["add_files", "remove_file"]:
            return [IsOwnerOfAnswer()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        user_groups = [group.name for group in user.groups.all()]

        # Update the base queryset to include grade prefetch
        base_queryset = self.queryset

        if self.action in ["list"]:
            if "Students" in user_groups:
                return base_queryset.filter(user=user)
            if "Teachers" in user_groups:
                teacher_groups = CourseGroup.objects.filter(teacher=user)
                # Only get enrollments for the teacher's groups
                student_enrollments = CourseEnrollment.objects.filter(
                    group__in=teacher_groups, role="student"
                )
                student_user_ids = set(enrollment.user.id for enrollment in student_enrollments)
                teacher_course_ids = set(group.course.id for group in teacher_groups)

                return base_queryset.filter(
                    user_id__in=student_user_ids,
                    task__course_id__in=teacher_course_ids,  # Explicit course restriction
                )
            elif "Admins" in user_groups:
                return base_queryset
        return base_queryset

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ["list", "retrieve", "teacher_review_answers"]:
            return AnswerReadSerializer
        elif self.action == "check":
            return AnswerReviewSerializer
        else:
            return AnswerWriteSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        """Override to prevent unauthorized content modifications"""
        user = self.request.user
        user_groups = [group.name for group in user.groups.all()]
        instance = serializer.instance

        # Additional check: Teachers/Admins can only modify answers from their students
        if any(group in user_groups for group in ["Teachers", "Admins"]):
            if not self._can_teacher_modify_answer(user, instance):
                raise PermissionDenied("You can only modify answers from your enrolled students")
        serializer.save()

    @staticmethod
    def _can_teacher_modify_answer(teacher_user, answer):
        """Check if teacher can modify this specific answer"""
        user_groups = [group.name for group in teacher_user.groups.all()]

        # Admins can modify any answer
        if "Admins" in user_groups:
            return True

        # Teachers can only modify answers from their course group students
        if "Teachers" in user_groups:
            teacher_groups = CourseEnrollment.objects.filter(
                user=teacher_user, role="teacher"
            ).values_list("group_id", flat=True)
            return CourseEnrollment.objects.filter(
                user=answer.user,
                course=answer.task.course,
                group_id__in=teacher_groups,
                role="student",
            ).exists()

        return False

    @action(detail=False, methods=["get"], url_path="teacher-review")
    def teacher_review_answers(self, request):
        """
        Get all answers from students enrolled in courses/groups where this teacher teaches.
        Teachers can only see answers from their own course groups.
        """
        user = request.user

        # Verify user is a teacher
        if not user.groups.filter(name="Teachers").exists():
            return Response(
                {"detail": "Only teachers can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get all course groups where this user is the teacher
        # teacher_groups = CourseGroup.objects.filter(teacher=user)
        enrollment_groups = CourseEnrollment.objects.filter(user=user, role="teacher").values_list(
            "group_id", flat=True
        )

        teacher_groups = CourseGroup.objects.filter(id__in=enrollment_groups)
        if not teacher_groups.exists():
            return Response(
                {"detail": "No course groups found for this teacher"}, status=status.HTTP_200_OK
            )

        # Get all students enrolled in these groups
        student_enrollments = CourseEnrollment.objects.filter(
            group__in=teacher_groups, role="student"
        ).select_related("user", "course", "group")

        # Extract course IDs and student user IDs
        course_ids = set(enrollment.course.id for enrollment in student_enrollments)
        student_user_ids = set(enrollment.user.id for enrollment in student_enrollments)

        # Get all answers from these students for tasks in these courses
        answers = (
            self.queryset.filter(user_id__in=student_user_ids, task__course_id__in=course_ids)
            .select_related("task__course", "user")
            .prefetch_related("files", "grade")  # Include grade prefetch
        )

        # Optional: Filter by status (e.g., only in_review answers)
        status_filter = request.query_params.get("status")
        if status_filter:
            answers = answers.filter(status=status_filter)

        # Optional: Filter by specific course
        course_filter = request.query_params.get("course_id")
        if course_filter:
            answers = answers.filter(task__course_id=course_filter)

        # Optional: Filter by specific group
        group_filter = request.query_params.get("group_id")
        if group_filter:
            # Get student IDs from specific group
            group_student_ids = CourseEnrollment.objects.filter(
                group_id=group_filter,
                group__teacher=user,  # Ensure teacher owns this group
                role="student",
            ).values_list("user_id", flat=True)
            answers = answers.filter(user_id__in=group_student_ids)

        # Order by most recent first
        answers = answers.order_by("-created_at")

        # Serialize and return
        serializer = self.get_serializer(answers, many=True)

        # Add metadata about teacher's groups for frontend
        groups_data = []
        for group in teacher_groups:
            groups_data.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "course": {"id": group.course.id, "name": group.course.name},
                    "student_count": CourseEnrollment.objects.filter(
                        group=group, role="student"
                    ).count(),
                }
            )

        return Response(
            {
                "answers": serializer.data,
                "teacher_groups": groups_data,
                "total_answers": answers.count(),
                "filters_available": {
                    "status_choices": Answer.Status.choices,
                    "courses": [
                        {"id": group.course.id, "name": group.course.name}
                        for group in teacher_groups
                    ],
                    "groups": [
                        {"id": group.id, "name": group.name, "course_id": group.course.id}
                        for group in teacher_groups
                    ],
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post", "patch"], url_path="check")
    def check(self, request, pk=None):
        """
        Review an answer by updating status and/or providing grade/feedback.

        POST: Create initial review (teacher first reviews the answer)
        PATCH: Update existing review (modify status and/or grade/feedback)

        This endpoint handles both Answer status updates and Grade creation/updates.
        """
        user = request.user
        answer = self.get_object()
        user_groups = [group.name for group in user.groups.all()]

        # Permission checks
        if not any(group in user_groups for group in ["Teachers", "Admins"]):
            return Response(
                {"detail": "Only teachers and admins can review answers"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not self._can_teacher_modify_answer(user, answer):
            return Response(
                {"detail": "You do not have permission to review this answer"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Use the updated review serializer
        serializer = AnswerReviewSerializer(
            answer,
            data=request.data,
            partial=(request.method == "PATCH"),
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)
        updated_answer = serializer.save()

        response_serializer = AnswerReadSerializer(updated_answer, context={"request": request})

        response_status = (
            status.HTTP_201_CREATED if request.method == "POST" else status.HTTP_200_OK
        )
        return Response(response_serializer.data, status=response_status)

    @action(detail=True, methods=["post"], url_path="add-files")
    def add_files(self, request, pk=None):
        answer = self.get_object()
        files = request.FILES.getlist("files")

        if not files:
            return Response({"detail": "No file selected"}, status=status.HTTP_400_BAD_REQUEST)

        current_files_count = answer.files.count()
        if current_files_count + len(files) > 30:
            return Response(
                {
                    "detail": f"Cannot add {len(files)} files. "
                    f"Maximum 30 files allowed per answer"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_files = []
        with transaction.atomic():
            for file in files:
                answer_file = AnswerFile.objects.create(answer=answer, file=file)
                created_files.append(answer_file)

        serializer = AnswerFileSerializer(created_files, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="remove-file/(?P<file_id>[^/.]+)")
    def remove_file(self, request, pk=None, file_id=None):
        """Remove a specific file from an answer"""
        answer = self.get_object()

        try:
            answer_file = answer.files.get(id=file_id)
            answer_file.delete()
            answer.plagiarism_status = Answer.PlagiarismStatus.pending_analysis
            answer.extracted_text = ""
            answer.analyzed_at = None
            answer.save(update_fields=["plagiarism_status", "extracted_text", "analyzed_at"])
            return Response(
                {"message": "File deleted successfully"}, status=status.HTTP_204_NO_CONTENT
            )
        except AnswerFile.DoesNotExist:
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["get"])
    def files(self, request, pk=None):
        answer = self.get_object()
        files = answer.files.all()
        serializer = AnswerFileSerializer(files, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Answers"])
class AnswerFileViewSet(ModelViewSet):
    """Separate viewset for file management if needed"""

    queryset = AnswerFile.objects.select_related("answer")
    serializer_class = AnswerFileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == "create":
            return AnswerFileUploadSerializer
        return AnswerFileSerializer

    def perform_create(self, serializer):
        answer = serializer.validated_data["answer"]
        if answer.files.count() >= 30:
            raise ValidationError("Maximum 30 files allowed per answer.")
        serializer.save()
        answer.plagiarism_status = Answer.PlagiarismStatus.pending_analysis
        answer.extracted_text = ""
        answer.analyzed_at = None
        answer.save(update_fields=["plagiarism_status", "extracted_text", "analyzed_at"])
