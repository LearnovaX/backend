import logging

from django.db import transaction
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from src.api.assignments.serializers import (
    ReassignTaskToUserSerializer,
    TaskReadSerializer,
    TaskWriteSerializer,
)
from src.api.submissions.serializers import AnswerReadSerializer
from src.apps.assignments.filters import TaskFilter
from src.apps.assignments.models import Task
from src.apps.common.permissions import IsAdmin, IsAdminOrTeacher, IsEnrolledToCourse
from src.apps.courses.models import CourseEnrollment
from src.apps.grades.models import Grade
from src.apps.submissions.models import Answer

logger = logging.getLogger(__name__)


@extend_schema(tags=["Tasks"])
class TaskModelViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.select_related("course", "created_by")
    serializer_class = TaskReadSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TaskFilter

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return TaskReadSerializer
        elif self.action in ["my_answer"]:
            return AnswerReadSerializer
        elif self.action == "reassign_to_user":
            return ReassignTaskToUserSerializer
        return TaskWriteSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        elif self.action == "my_answer":
            return [IsEnrolledToCourse()]
        elif self.action in ["reassign_to_all", "reassign_to_user"]:
            return [IsAdmin()]
        return [IsAdminOrTeacher()]

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        course = instance.course
        user = self.request.user
        if user.groups.filter(name="Teachers").exists():
            if not (
                course.allow_teachers_to_manage_tasks
                and CourseEnrollment.objects.filter(
                    user=user, course=course, role="teacher"
                ).exists()
            ):
                logger.warning(
                    f"tasks. User with id {self.request.user.pk} tried to create "
                    f"task for course with id {course.pk} {course.title}, "
                    f"but the tasks management for teachers is not allowed in this course"
                )
                raise PermissionDenied("You cannot manage tasks for this course.")

        def _log():
            logger.info(
                f"tasks. Task created by user id {self.request.user.pk}."
                f" new task id: {instance.id}",
            )

        transaction.on_commit(_log)

    def perform_update(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        course = instance.course
        user = self.request.user
        if user.groups.filter(name="Teachers").exists():
            if not (
                course.allow_teachers_to_manage_tasks
                and CourseEnrollment.objects.filter(
                    user=user, course=course, role="teacher"
                ).exists()
            ):
                logger.warning(
                    f"tasks. User with id {self.request.user.pk} tried to update "
                    f"task '{instance.pk}' for course with id {course.pk} {course.title}, "
                    f"but the tasks management for teachers is not allowed in this course"
                )
                raise PermissionDenied("You cannot manage tasks for this course.")

        def _log():
            logger.info(
                f"tasks. Task Updated by user id {self.request.user.pk}. new task id: {instance.id}"
            )

        transaction.on_commit(_log)

    def perform_destroy(self, instance):
        course = instance.course
        user = self.request.user
        if user.groups.filter(name="Teachers").exists():
            if not (
                course.allow_teachers_to_manage_tasks
                and CourseEnrollment.objects.filter(
                    user=user, course=course, role="teacher"
                ).exists()
            ):
                logger.warning(
                    f"tasks. User with id {self.request.user.pk} tried to delete "
                    f"task '{instance.pk}' for course with id {course.pk} {course.title}, "
                    f"but the tasks management for teachers is not allowed in this course"
                )
                raise PermissionDenied("You cannot manage tasks for this course.")
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])

        # instance.delete()
        def _log():
            logger.info(
                f"tasks. Task deleted by user id {self.request.user.pk}."
                f" deleted task id: {instance.id}",
            )

        transaction.on_commit(_log)

    @action(methods=["post"], detail=False, url_path="reassign-to-user")
    @method_decorator(transaction.atomic)
    def reassign_to_user(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                f"tasks.reassign_to_user: Request user with {request.user.pk} "
                f"tried to reassign task id {request.data.get('task_id', None)}"
                f"to user id {request.data.get('user_id', None)}, but errors occurred:"
                f" {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        logger.info(
            f"tasks.reassign_to_user: Request user with id {request.user.pk}"
            f"reassigned task id {request.data.get('task_id', None)}"
            f" to user id {request.data.get('user_id', None)} "
        )
        return Response(
            {"detail": "Successfully reassigned task to user"}, status=status.HTTP_200_OK
        )

    @action(methods=["post"], detail=True, url_path="reassign-to-all")
    @method_decorator(transaction.atomic)
    def reassign_to_all(self, request, pk=None):
        task: Task = self.get_object()
        Grade.objects.filter(answer__task=task).delete()
        Answer.objects.filter(task=task).delete()
        logger.info(
            f"tasks.reassign_to_all: Request user with {request.user.pk} "
            f"reassigned task with id {task.pk} to all users"
        )
        return Response({"detail": f"Task {task.name} has been reassigned to all users"})

    @action(methods=["get"], detail=True, url_path="my-answer")
    def my_answer(self, request, pk=None):
        task: Task = self.get_object()
        answer = (
            Answer.objects.select_related("task", "user__profile", "grade__graded_by")
            .prefetch_related("files")
            .filter(task=task, user=request.user)
            .first()
        )

        if not answer:
            return Response(
                {"detail": f"User {request.user.pk} doesn't have any submitted answer"},
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(answer)
        return Response(serializer.data)
