from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from src.apps.common.permissions import IsAdminOrTeacher
from src.apps.grades.models import Grade

from ...apps.courses.models import CourseGroup
from .serializers import GradeReadSerializer, GradeWriteSerializer


@extend_schema(tags=["Grades"])
class GradeModelViewSet(ModelViewSet):
    queryset = Grade.objects.select_related("answer", "graded_by").all()
    serializer_class = GradeReadSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update"]:
            return [IsAdminOrTeacher()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return GradeWriteSerializer
        return GradeReadSerializer

    def get_queryset(self):
        user = self.request.user

        if user.groups.filter(name="Admins").exists():
            return self.queryset
        if user.groups.filter(name="Teachers").exists():
            teacher_groups = CourseGroup.objects.filter(
                members__user=user, members__role="teacher"
            ).distinct()
            return (
                self.queryset.filter(
                    answer__user__enrollments__group__in=teacher_groups,
                    answer__user__enrollments__role="student",
                )
                .select_related(
                    "answer__user",
                    "answer__task",
                    "answer__task__course",
                    "graded_by",
                )
                .distinct()
            )

        return self.queryset.filter(answer__user=user)

    def perform_create(self, serializer):
        serializer.save(graded_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(graded_by=self.request.user)
