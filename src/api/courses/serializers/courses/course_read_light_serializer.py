from rest_framework import serializers

from src.apps.courses.models import Course, CourseEnrollment


class CourseReadLightSerializer(serializers.ModelSerializer):

    class Meta:
        model = Course
        fields = ["id", "name"]


class CourseReadLightWithRoleSerializer(CourseReadLightSerializer):
    can_manage_tasks = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta(CourseReadLightSerializer.Meta):
        fields = ["id", "name", "can_manage_tasks", "role", "allow_teachers_to_manage_tasks"]

    def get_can_manage_tasks(self, obj: Course) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user:
            return False

        group_names = self.get_user_group_names(user)

        if "Admins" in group_names:
            return True

        enrollments = getattr(obj, "current_user_enrollments", None)
        if enrollments is not None:
            if not enrollments:
                return False
        else:
            if not CourseEnrollment.objects.filter(user=user, course=obj).exists():
                return False

        if "Teachers" in group_names and obj.allow_teachers_to_manage_tasks:
            return True
        return False

    def get_role(self, obj: Course) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user:
            return "Not enrolled"

        group_names = self.get_user_group_names(user)

        if "Admins" in group_names:
            return "Admin"

        enrollments = getattr(obj, "current_user_enrollments", None)
        if enrollments is not None:
            if not enrollments:
                return "Not enrolled"
        else:
            if not CourseEnrollment.objects.filter(user=user, course=obj).exists():
                return "Not enrolled"

        if "Teachers" in group_names:
            return "Teacher"
        if "Students" in group_names:
            return "Student"

        return "Not enrolled"

    @staticmethod
    def get_user_group_names(user):
        if not hasattr(user, "_cached_group_names"):
            user._cached_group_names = set(user.groups.values_list("name", flat=True))
        return user._cached_group_names
