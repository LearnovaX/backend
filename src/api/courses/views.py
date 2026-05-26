import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from src.api.assignments.serializers import TaskReadSerializer
from src.api.courses.serializers import (
    AddStudentsSerializer,
    AddTeachersSerializer,
    CourseEnrollmentReadSerializer,
    CourseEnrollmentWriteSerializer,
    CourseExportSerializer,
    CourseGroupReadSerializer,
    CourseGroupWriteSerializer,
    CourseReadSerializer,
    CourseStatisticsSerializer,
    CourseStudentsInfoSerializer,
    CourseWriteSerializer,
    ReassignCourseSerializer,
    RemoveFromCourseSerializer,
    RemoveStudentsSerializer,
    RemoveTeachersSerializer,
    StudentTasksStatusSerializer,
    StudentTaskViewForCourseSerializer,
    TeacherStudentsSerializer,
)
from src.api.courses.serializers.categories import CategorySerializer
from src.api.courses.serializers.course_group_serializers.course_group_list_serializer import (
    CourseGroupListSerializer,
)
from src.api.courses.serializers.courses.course_read_light_serializer import (
    CourseReadLightSerializer,
)
from src.api.submissions.serializers import AnswerReadSerializer
from src.api.users.serializers import AllUsersSerializerLight, UserSerializer
from src.apps.common.permissions import (
    IsAdmin,
    IsAdminOrTeacher,
    IsEnrolledOrAdmin,
    IsEnrolledToCourse,
)
from src.apps.common.utils.files.export_courses import export_courses_to_csv, export_courses_to_xlsx
from src.apps.courses.cache import (
    COURSES_LIST_TTL,
    COURSE_GROUPS_LIST_TTL,
    COURSE_GROUPS_PAGE_TTL,
    courses_list_cache_key,
    course_groups_list_cache_key,
    course_groups_page_cache_key,
    COURSES_LIGHT_LIST_TTL,
    course_light_list_cache_key,
)
from src.apps.courses.filters import CourseFilter
from src.apps.courses.models import Category, Course, CourseEnrollment, CourseGroup
from src.apps.submissions.models import Answer
from src.apps.users.filters import UserFilter
from src.apps.users.models import User
from src.apps.users.pagination import AdminUserPagination

logger = logging.getLogger(__name__)


@extend_schema(tags=["Courses"])
class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseReadSerializer
    queryset = Course.objects.select_related("author", "category").all().order_by("name")
    filter_backends = [DjangoFilterBackend]
    filterset_class = CourseFilter


    def get_permissions(self):
        if self.action in ["list", "retrieve", "my_courses", "student_tasks_statuses"]:
            # TODO -> fix student_tasks_statuses permissions
            return [IsAuthenticated()]
        elif self.action in ["statistics", "students", "groups", "teachers"]:
            return [IsAuthenticated()]
            # TODO -> add basic statistics, like tasks count for student
            # return [IsAdminOrTeacher()]
        if self.action == "tasks":
            return [IsAuthenticated(), IsEnrolledOrAdmin()]
        return [IsAdmin()]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return CourseWriteSerializer
        elif self.action == "light_list":
            return CourseReadLightSerializer
        elif self.action == "statistics":
            return CourseStatisticsSerializer
        elif self.action == "export_courses":
            return CourseExportSerializer
        elif self.action == "student_tasks_statuses":
            return StudentTasksStatusSerializer
        elif self.action in ["students", "all_user_courses_and_groups"]:
            return CourseStudentsInfoSerializer
        elif self.action == "view_student_all_tasks":
            return StudentTaskViewForCourseSerializer
        elif self.action == "reassign":
            return ReassignCourseSerializer
        elif self.action == "remove_from_course":
            return RemoveFromCourseSerializer
        elif self.action == "tasks":
            return TaskReadSerializer
        return CourseReadSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if "Admins" not in user.cached_group_names:
            enrolled_ids = CourseEnrollment.objects.filter(user=user).values_list(
                "course_id", flat=True
            )
            qs = qs.filter(id__in=enrolled_ids)

        return qs.prefetch_related(
            Prefetch(
                "enrollments",
                queryset=CourseEnrollment.objects.filter(user=user).select_related("user"),
                to_attr="current_user_enrollments",
            )
        )

    def list(self, request, *args, **kwargs):
        cache_key = courses_list_cache_key(request.query_params)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)
        
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, COURSES_LIST_TTL)
        return response

    @action(methods=["get"], detail=False, url_path="my-courses")
    def my_courses(self, request):
        user = request.user
        course_ids = CourseEnrollment.objects.filter(user=user).values_list("course", flat=True)
        courses = Course.objects.filter(pk__in=course_ids).select_related("author", "category")
        serializer = CourseReadSerializer(courses, many=True, context={"request": request})
        return Response(serializer.data)

    @action(methods=["get"], detail=True)
    def tasks(self, request, pk=None):
        course: Course = self.get_object()
        course_tasks = course.tasks.all().select_related("course__category")
        serializer = TaskReadSerializer(course_tasks, many=True)
        return Response(serializer.data)

    @action(methods=["get"], detail=True)
    def groups(self, request, pk=None):
        course: Course = self.get_object()
        cache_key = course_groups_page_cache_key(course.id)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        groups = course.groups.select_related("course__category", "course__author")
        # TODO -> optimize
        serializer = CourseGroupReadSerializer(groups, many=True)
        data = serializer.data
        cache.set(cache_key, data, COURSE_GROUPS_PAGE_TTL)
        return Response(data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="teachers")
    def teachers(self, request, pk=None):
        course = self.get_object()
        teacher_ids = (
            CourseEnrollment.objects.filter(course=course, role="teacher")
            .values_list("user_id", flat=True)
            .distinct()
        )
        # TODO optimize
        teachers = User.objects.filter(id__in=teacher_ids)
        serializer = UserSerializer(teachers, many=True, context={"request": request})
        return Response(serializer.data, status=200)

    @action(methods=["get"], detail=False, url_path="statistics")
    def statistics(self, request, pk=None):
        qs = Course.objects.annotate(
            students_count=Count(
                "enrollments__user",
                filter=Q(enrollments__role="student"),
                distinct=True,
            ),
            teachers_count=Count(
                "enrollments__user",
                filter=Q(enrollments__role="teacher"),
                distinct=True,
            ),
            groups_count=Count(
                "groups",
                filter=Q(groups__is_deleted=False),
                distinct=True,
            ),
            tasks_count=Count(
                "tasks",
                filter=Q(tasks__is_deleted=False),
                distinct=True,
            ),
        )

        serializer = self.get_serializer(qs, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=False, url_path="export-courses")
    def export_courses(self, request):
        file_type = request.query_params.get("file_type")
        if file_type not in ["csv", "xlsx"]:
            logger.warning(
                f"courses.courses.export_courses received invalid file type: {file_type}. "
                f"user id: {request.user.pk}"
            )
            return Response({"detail": "Invalid file format"}, status=status.HTTP_400_BAD_REQUEST)

        qs = Course.objects.select_related("author", "category").annotate(
            students_count=Count(
                "enrollments__user", filter=Q(enrollments__role="student"), distinct=True
            ),
            teachers_count=Count(
                "enrollments__user", filter=Q(enrollments__role="teacher"), distinct=True
            ),
            groups_count=Count("groups", filter=Q(groups__is_deleted=False), distinct=True),
            tasks_count=Count("tasks", filter=Q(tasks__is_deleted=False), distinct=True),
        )

        data = self.get_serializer(qs, many=True).data
        if file_type == "csv":
            return export_courses_to_csv(data)
        return export_courses_to_xlsx(data)

    @transaction.atomic
    @action(methods=["post"], detail=True, url_path="deactivate")
    def deactivate(self, request, pk=None):
        course = self.get_object()
        course.is_active = False
        course.save(update_fields=["is_active"])
        logger.info(f"courses.course.deactivate. {course.id} is deactivated by {request.user.pk}")
        return Response({"message": "Course deactivated"}, status=status.HTTP_200_OK)

    @transaction.atomic
    @action(methods=["post"], detail=True, url_path="activate")
    def activate(self, request, pk=None):
        course = self.get_object()
        course.is_active = True
        course.save(update_fields=["is_active"])
        logger.info(f"courses.course.activate. {course.id} is activated by {request.user.pk}")
        return Response({"message": "Course activated"}, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])
        logger.info(f"courses.course. Course deleted. {instance.pk} by {self.request.user.pk}")

    @action(methods=["get"], detail=True, url_path="students")
    def students(self, request, pk=None):
        course: Course = self.get_object()
        students = CourseEnrollment.objects.filter(course=course, role="student").select_related(
            "user", "group", "course"
        )
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="student-tasks-statuses")
    def student_tasks_statuses(self, request, pk=None):
        course: Course = self.get_object()
        user = request.user
        tasks = course.tasks.all().prefetch_related(
            Prefetch(
                "answers",
                queryset=Answer.objects.filter(user=user).prefetch_related("grade"),
                to_attr="user_answers",
            )
        )

        serializer = self.get_serializer(tasks, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="view-student")
    def view_student_all_tasks(self, request, pk=None):
        user_id = request.query_params.get("user_id")
        if not User.objects.filter(pk=user_id).exists():
            return Response({"detail": "Invalid user_id"}, status=status.HTTP_400_BAD_REQUEST)

        course: Course = self.get_object()
        qs = course.tasks.prefetch_related(
            Prefetch(
                "answers",
                queryset=Answer.objects.filter(user_id=user_id)
                .select_related("user", "task__course")
                .prefetch_related("files", "grade__graded_by"),
                to_attr="student_answer",
            )
        )
        serializer = self.get_serializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=False, url_path="all-user-courses-and-groups")
    def all_user_courses_and_groups(self, request, pk=None):
        user_id = request.query_params.get("user_id")
        if not User.objects.filter(pk=user_id).exists():
            return Response({"detail": "Invalid user_id"}, status=status.HTTP_400_BAD_REQUEST)

        enrollments = CourseEnrollment.objects.filter(user_id=user_id)
        serializer = self.get_serializer(enrollments, many=True)
        return Response(serializer.data)

    @action(methods=["post"], detail=True, url_path="reassign")
    def reassign(self, request, pk=None):
        course: Course = self.get_object()
        serializer = self.get_serializer(data=request.data, context={"course": course})
        if not serializer.is_valid():
            logger.warning(
                "courses.reassign | user=%s tried to reassign course=%s to users=%s | errors=%s",
                request.user.pk,
                course.id,
                request.data.get("user_ids", []),
                serializer.errors,
            )
            return Response(serializer.errors, status=400)

        reassigned = serializer.save()
        logger.info(
            "courses.reassign | user=%s reassigned course=%s to users=%s",
            request.user.pk,
            course.id,
            request.data.get("user_ids", []),
        )

        return Response(
            {"detail": f"successfully reassigned '{course.pk}' course for {reassigned} users"}
        )

    @action(methods=["post"], detail=True, url_path="accept")
    def accept_course(self, request, pk=None):
        course: Course = self.get_object()  # noqa E402
        user_ids = request.data.get("user_ids")
        print(user_ids)
        # TODO
        return Response({"detail": "successfully accepted course"})

    @action(methods=["post"], detail=True, url_path="remove")
    def remove_from_course(self, request, pk=None):
        course: Course = self.get_object()  # noqa E402
        serializer = self.get_serializer(data=request.data, context={"course": course})
        if not serializer.is_valid():
            logger.warning(
                "courses.remove | user=%s tried to remove to users=%s from course=%s| errors=%s",
                request.user.pk,
                course.id,
                request.data.get("user_ids", []),
                serializer.errors,
            )
            return Response(serializer.errors, status=400)

        removed = serializer.save()
        logger.info(
            "courses.remove | user=%s removed users=%s from course=%s",
            request.user.pk,
            course.id,
            request.data.get("user_ids", []),
        )

        return Response(
            {"detail": f"successfully removed {removed} students from course {course.name}"}
        )

    @action(methods=["get"], detail=False, url_path="light-list")
    def light_list(self, request):
        cache_key = course_light_list_cache_key(request.query_params)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        qs = super().get_queryset()
        serializer = self.get_serializer(qs, many=True)
        data = serializer.data
        cache.set(cache_key, data, COURSES_LIGHT_LIST_TTL)
        return Response(data)


@extend_schema(tags=["Course Groups"])
class CourseGroupViewSet(viewsets.ModelViewSet):
    serializer_class = CourseGroupReadSerializer
    queryset = CourseGroup.objects.select_related("course")

    # filter_backends = [DjangoFilterBackend]
    # filter_class = CourseGroupFilter

    def get_permissions(self):
        if self.action in ["my_groups", "enroll_by_token", "list", "retrieve"]:
            return [IsAuthenticated()]
        elif self.action in ["assign_teacher", "add_students", "refresh_token", "remove_students"]:
            return [IsAdmin()]
        elif self.action == "members":
            return [IsAdminOrTeacher()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = CourseGroup.objects.select_related("course__category", "course__author")

        params = self.request.query_params
        search = params.get("search")
        is_active_param = params.get("is_active")

        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(course__name__icontains=search)
                | Q(members__role="teacher", members__user__first_name__icontains=search)
                | Q(members__role="teacher", members__user__last_name__icontains=search)
                | Q(members__role="teacher", members__user__email__icontains=search)
            ).distinct()

        if is_active_param is None:
            qs = qs.filter(is_active=True)
        else:
            val = str(is_active_param).strip().lower()
            if val in {"true", "1", "yes"}:
                qs = qs.filter(is_active=True)
            elif val in {"false", "0", "no"}:
                qs = qs.filter(is_active=False)
            elif val in {"all"}:
                pass
            else:
                qs = qs.filter(is_active=True)

        ordering = params.get("ordering")
        if ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-created_at")

        return qs.annotate(
            members_count=Count("members", distinct=True),
            students_count=Count("members", filter=Q(members__role="student"), distinct=True),
        )

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return CourseGroupWriteSerializer
        elif self.action == "add_students":
            return AddStudentsSerializer
        elif self.action == "remove_students":
            return RemoveStudentsSerializer
        elif self.action == "add_teachers":
            return AddTeachersSerializer
        elif self.action == "remove_teachers":
            return RemoveTeachersSerializer
        elif self.action == "light_list":
            return CourseGroupListSerializer
        return CourseGroupReadSerializer

    def list(self, request, *args, **kwargs):
        params = request.query_params.copy()
        params["__is_admin"] = "1" if request.user.groups.filter(name="Admins").exists() else "0"
        cache_key = course_groups_list_cache_key(params)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, COURSE_GROUPS_LIST_TTL)
        return response

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.self_registration:
            instance.generate_unique_token(
                hours_valid=instance.token_validity_hours, days_valid=instance.token_validity_days
            )
        logger.info(f"courses.group.create. {instance.name} by {self.request.user.pk}")

    def perform_update(self, serializer):
        old_instance = self.get_object()
        old_self_registration = old_instance.self_registration

        instance = serializer.save()

        if instance.self_registration and not old_self_registration:
            instance.generate_unique_token(
                hours_valid=instance.token_validity_hours, days_valid=instance.token_validity_days
            )
        elif not instance.self_registration and old_self_registration:
            instance.invalidate_token()
        elif instance.self_registration:
            if not instance.registration_token:
                instance.generate_unique_token(
                    hours_valid=instance.token_validity_hours,
                    days_valid=instance.token_validity_days,
                )
            else:
                old_hours = old_instance.token_validity_hours
                old_days = old_instance.token_validity_days
                new_hours = instance.token_validity_hours
                new_days = instance.token_validity_days

                if old_hours != new_hours or old_days != new_days:
                    instance.generate_unique_token(hours_valid=new_hours, days_valid=new_days)
        logger.info(f"courses.group.update. {instance.name} by {self.request.user.pk}")

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()
        logger.info(f"courses.group.delete. {instance.pk} by {self.request.user.pk}")

    @action(methods=["post"], detail=True, url_path="deactivate")
    def deactivate(self, request, pk=None):
        group = self.get_object()
        group.is_active = False
        group.save(update_fields=["is_active"])
        logger.info(f"courses.group.deactivate. {group.pk} by {self.request.user.pk}")
        return Response({"message": "Group deactivated"})

    @action(methods=["get"], detail=False)
    def my_groups(self, request):
        user = request.user
        group_ids = CourseEnrollment.objects.filter(user=user).values_list("group", flat=True)
        group_ids = [gid for gid in group_ids if gid is not None]
        groups = CourseGroup.objects.filter(pk__in=group_ids)
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add-teachers")
    def add_teachers(self, request, pk=None):
        group = self.get_object()
        ser = self.get_serializer(data=request.data, context={"request": request, "group": group})
        ser.is_valid(raise_exception=True)
        if not ser.is_valid():
            logger.warning(f"courses.group.add-teachers. {ser.errors} by {request.user.pk}")
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        result = ser.save()
        data = [
            {
                "id": e.user.id,
                "first_name": e.user.first_name,
                "last_name": e.user.last_name,
                "email": e.user.email,
            }
            for e in result["created"]
        ]
        logger.info(f"courses.group.add-teachers. Added {data} teachers by {request.user.pk}")
        return Response({"added": data, "errors": result.get("errors", [])}, status=201)

    @action(detail=True, methods=["post"], url_path="remove-teachers")
    def remove_teachers(self, request, pk=None):
        group = self.get_object()
        ser = self.get_serializer(data=request.data, context={"request": request, "group": group})
        if not ser.is_valid():
            logger.warning(f"courses.group.remove-teachers. {ser.errors} by {request.user.pk}")
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        result = ser.save()
        logger.info(f"course.group.remove-teachers. Removed {result} teachers by {request.user.pk}")
        return Response(result, status=200)

    @extend_schema(
        request=AddStudentsSerializer,
        responses={200: OpenApiResponse(response=CourseEnrollmentReadSerializer(many=True))},
    )
    @action(detail=True, methods=["post"], url_path="add-students")
    def add_students(self, request, pk=None):
        """
        Add multiple students to this group.
        Request Body: {"user_ids": [1,2,3]}
        Allowed: only admins.
        """
        group = self.get_object()
        serializer = self.get_serializer(
            data=request.data, context={"request": request, "group": group}
        )
        if not serializer.is_valid():
            logger.warning(f"courses.group.add-students. {serializer.errors} by {request.user.pk}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        result = serializer.save()

        enrollments_qs = result.get("created")
        errors = result.get("errors", [])

        response_serializer = CourseEnrollmentReadSerializer(
            instance=enrollments_qs, many=True, context={"request": request}
        )
        logger.info(
            f"course.group.add-students. Data {serializer.data}" f"\nadded by {request.user.pk}"
        )
        return Response(
            {"enrolled": response_serializer.data, "errors": errors}, status=status.HTTP_201_CREATED
        )

    @extend_schema(responses={200: OpenApiResponse(response=serializers.DictField())})
    @action(detail=True, methods=["post"], url_path="remove-students")
    def remove_students(self, request, pk=None):
        """
        Remove users from this group (deletes the enrollments for this course).
        Body: {"user_ids": [<id1>, "id2", ...]}
        Permission: admin
        """
        group = self.get_object()
        serializer = RemoveStudentsSerializer(
            data=request.data, context={"request": request, "group": group}
        )
        if not serializer.is_valid():
            logger.warning(
                f"course.group.remove-students. {serializer.errors} by {request.user.pk}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        result = serializer.save()
        logger.info(f"course.group.remove-students. Data: {result}\n removed by {request.user.pk}")
        return Response(result, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        """
        List members of this group (students, assistants). Teachers may see all.
        """
        group = self.get_object()
        counts = CourseEnrollment.objects.filter(group=group).aggregate(
            members_count=Count("id"), students_count=Count("id", filter=Q(role="student"))
        )
        enrollments = (
            CourseEnrollment.objects.filter(group=group)
            .select_related(
                "user__profile",
                "group__course__category",
                "group__course__author",
            )
            .prefetch_related(
                # if CourseGroupReadSerializer is used inside
                Prefetch(
                    "group__members",
                    queryset=CourseEnrollment.objects.select_related("user__profile"),
                )
            )
        )
        context = {"request": request, "group_counts": {group.id: counts}}
        serializer = CourseEnrollmentReadSerializer(enrollments, many=True, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["post"], detail=True, url_path="refresh-token")
    def refresh_token(self, request, pk=None):
        """
        Manually refresh the registration token for a group.
        Only available for admins.
        """
        group = self.get_object()

        if not group.self_registration:
            logger.warning(
                f"courses.group.refresh-token. User with id {request.user.pk}"
                f"tried to refresh token for group {group.pk}, but self-registration"
                f" is not enabled for this group"
            )
            return Response(
                {"detail": "Self-registration is not enabled for this group"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        group.generate_unique_token(
            hours_valid=group.token_validity_hours, days_valid=group.token_validity_days
        )

        serializer = self.get_serializer(group)
        logger.info(
            f"courses.group.refresh-token. Group {group.pk} refreshed token by {request.user.pk}"
        )
        return Response(
            {"message": "Token refreshed successfully", "group": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(methods=["get"], detail=False, url_path="enroll/(?P<token>[^/.]+)")
    def enroll_by_token(self, request, token=None):
        try:
            group = CourseGroup.objects.get(registration_token=token, self_registration=True)
            if group.is_token_expired():
                logger.warning(
                    f"courses.group.enroll-by-token. User with id {request.user.pk}"
                    f"tried to enroll token for group {group.pk}, but token is expired"
                )
                return Response({"detail": "Token is expired"}, status=status.HTTP_403_FORBIDDEN)
        except CourseGroup.DoesNotExist:
            logger.warning(
                f"courses.group.enroll-by-token. User with id {request.user.pk}"
                f"tried to enroll token for some group, but no group with"
                f" token {token} exists, token is invalid"
            )

            return Response(
                {"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST
            )

        if CourseEnrollment.objects.filter(user=request.user, group=group).exists():
            logger.warning(
                f"courses.group.enroll-by-token. User with id {request.user.pk}"
                f" tried to enroll to group {group.pk}, but user already enrolled to this group"
            )
            return Response(
                {"detail": "User is already enrolled"}, status=status.HTTP_400_BAD_REQUEST
            )

        if group.students_limit and group.members.count() >= group.students_limit:
            logger.warning(
                f"courses.group.enroll-by-token. User with "
                f"id {request.user.pk} tried to enroll"
                f" to group {group.pk}, but the students limit is reached"
            )
            return Response({"detail": "Too many students"}, status=status.HTTP_400_BAD_REQUEST)

        CourseEnrollment.objects.create(
            user=request.user,
            group=group,
            course=group.course,
            role="student",
        )
        logger.info(
            f"courses.group.enroll-by-token. User"
            f" with id {request.user.pk} enrolled to group {group.pk}"
        )
        return Response({"message": f"You have been enrolled in {group.name}."})

    @action(methods=["get"], detail=False, url_path="light-list")
    def light_list(self, request):
        qs = super().get_queryset()
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(tags=["All Users"])
class AllUsersViewSet(viewsets.GenericViewSet):
    serializer_class = AllUsersSerializerLight
    queryset = User.objects.all().select_related("profile")
    pagination_class = AdminUserPagination

    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter

    @action(methods=["get"], detail=False, url_path="all-users")
    def all_users(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(
                page, many=True, context={"include_profile_photo": True}
            )
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True, context={"include_profile_photo": True})
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Course Enrollments"])
class CourseEnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = CourseEnrollmentReadSerializer
    queryset = CourseEnrollment.objects.select_related("user", "group", "course")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return CourseEnrollmentWriteSerializer
        elif self.action == "teacher_students":
            return TeacherStudentsSerializer
        return CourseEnrollmentReadSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve", "my_enrollments"]:
            return [IsAuthenticated()]
        elif self.action == "my_answers":
            return [IsEnrolledToCourse()]
        elif self.action == "teacher_students":
            return [IsAdminOrTeacher()]
        return [IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="Admins").exists():
            return self.queryset
        if user.groups.filter(name="Teachers").exists():
            # courses where the user is enrolled as teacher
            teacher_course_ids = CourseEnrollment.objects.filter(
                user=user, role="teacher"
            ).values_list("course_id", flat=True)
            return self.queryset.filter(course_id__in=teacher_course_ids).distinct()
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        instance = serializer.save()
        transaction.on_commit(
            lambda: logger.info(
                f"courses.enrollments. Course enrollment"
                f" created: {instance.pk} by {self.request.user}"
            )
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        transaction.on_commit(
            lambda: logger.info(
                f"courses.enrollments. Course enrollment"
                f" updated: {instance.pk} by {self.request.user}"
            )
        )

    def perform_destroy(self, instance):
        pk = instance.pk
        super().perform_destroy(instance)
        transaction.on_commit(
            lambda: logger.info(
                f"courses.enrollments. Course enrollment" f" deleted: {pk} by {self.request.user}"
            )
        )

    @action(methods=["get"], detail=False)
    def my_enrollments(self, request):
        user = request.user
        enrolled_courses = CourseEnrollment.objects.filter(user=user)
        serializer = self.get_serializer(enrolled_courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=True, url_path="my-answers")
    def my_answers(self, request, pk=None):
        user = request.user
        enrolled_course: CourseEnrollment = self.get_object()
        answers = Answer.objects.filter(user=user, task__course=enrolled_course.course)
        serializer = AnswerReadSerializer(answers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["get"], detail=False, url_path="teacher-students")
    def teacher_students(self, request):
        """
        Returns a list of all students where teacher is enrolled.
        """
        user = request.user
        teacher_enrollment = CourseEnrollment.objects.filter(user=user, role="teacher").values_list(
            "group_id", flat=True
        )
        students = CourseEnrollment.objects.filter(group_id__in=teacher_enrollment, role="student")
        serializer = self.get_serializer(students, many=True, context={"request": request})

        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Categories"])
class CategoryModelViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdmin()]
        return [IsAuthenticated()]

    @action(methods=["get"], detail=True, url_path="courses")
    def courses(self, request, pk=None):
        category = self.get_object()
        courses = category.courses.all()
        serializer = CourseReadSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # TODO
    # @action(methods=['get'], detail=False, url_path="courses-count")
    # def course_count(self, request):
    #     pass
