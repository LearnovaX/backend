from rest_framework.permissions import BasePermission


def is_admin(user) -> bool:
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.groups.filter(name="Admins").exists())
    )


def is_teacher(user) -> bool:
    return bool(user and user.is_authenticated and user.groups.filter(name="Teachers").exists())


class IsTeacherOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return is_admin(user) or is_teacher(user)
