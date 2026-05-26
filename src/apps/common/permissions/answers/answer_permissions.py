from rest_framework import permissions

from src.apps.submissions.models import Answer


class IsOwnerOfAnswer(permissions.BasePermission):
    def has_object_permission(self, request, view, obj: Answer):
        return request.user == obj.user


class IsTeacherOrAdminCanEditStatus(permissions.BasePermission):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in ["PATCH", "PUT"]:
            if "status" in request.data and request.user.groups.filter(name="Students").exists():
                return False
        return True
