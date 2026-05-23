from rest_framework.permissions import BasePermission

from src.apps.assignments.models import Task
from src.apps.courses.models import CourseEnrollment
from src.apps.submissions.models import Answer


class IsEnrolledToCourse(BasePermission):
    def has_object_permission(self, request, view, obj: Answer | CourseEnrollment | Task):
        user = request.user
        if isinstance(obj, CourseEnrollment):
            return CourseEnrollment.objects.filter(user=user, course=obj.course).exists()
        elif isinstance(obj, Task):
            return CourseEnrollment.objects.filter(user=user, course=obj.course).exists()
        return CourseEnrollment.objects.filter(user=user, course=obj.task.course).exists()


class IsEnrolledOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.groups.filter(name="Admins").exists():
            return True
        return CourseEnrollment.objects.filter(user=user, course=obj).exists()
