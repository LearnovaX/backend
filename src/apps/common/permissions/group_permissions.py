from rest_framework.permissions import BasePermission

# from src.apps.courses.models import CourseEnrollment


class IsAdmin(BasePermission):
    """
    Allows access only to users in the 'admin' group or superusers.
    """

    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and (user.is_superuser or user.groups.filter(name="Admins").exists())
        )


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user and user.is_authenticated and (user.groups.filter(name="Teachers").exists())


class IsAdminOrTeacher(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.groups.filter(name="Admins").exists()
                or user.groups.filter(name="Teachers").exists()
            )
        )

    # def has_object_permission(self, request, view, obj: CourseEnrollment):
    #     user = request.user
    #     enrollments = list(
    #       CourseEnrollment.objects.filter(user=user, role='teacher').values_list('pk', flat=True))
    #     has_enrolled = obj.pk in enrollments
    #     print(f'{enrollments=}, {obj.pk=}, {user.pk=}, {has_enrolled=}')
    #     return (
    #             user
    #             and user.is_authenticated
    #             and (
    #                     (user.is_superuser
    #                      or user.groups.filter(name="Admins").exists()
    #                      or user.groups.filter(name="Teachers").exists())
    #                     and (user.is_superuser or has_enrolled)
    #             )
    #     )
