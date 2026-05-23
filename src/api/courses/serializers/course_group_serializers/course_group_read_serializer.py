from rest_framework import serializers

from src.api.courses.serializers.courses.course_read_light_serializer import (
    CourseReadLightSerializer,
)

# from src.api.users.serializers import AllUsersSerializerLight
from src.apps.courses.models import CourseGroup


class CourseGroupReadSerializer(serializers.ModelSerializer):
    teachers = serializers.SerializerMethodField()
    course = CourseReadLightSerializer(read_only=True)
    registration_link = serializers.SerializerMethodField()
    is_token_expired = serializers.SerializerMethodField()
    token_status = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseGroup
        fields = [
            "id",
            "name",
            "course",
            "teachers",
            "members_count",
            "students_count",
            "students_limit",
            "self_registration",
            "token_validity_hours",
            "token_validity_days",
            "registration_link",
            "token_expires_at",
            "is_token_expired",
            "token_status",
        ]

    def get_registration_link(self, obj: CourseGroup):
        request = self.context.get("request")
        if request and request.user:
            group_names = self.get_user_group_names(request.user)
            if "Admins" in group_names:
                if obj.self_registration and obj.is_token_expired():
                    return "Registration link is expired"
                return obj.registration_link
        return None

    def get_is_token_expired(self, obj: CourseGroup):
        """Check if the registration token is expired"""
        return obj.is_token_expired()

    def get_token_status(self, obj: CourseGroup):
        """Get human-readable token status"""
        if not obj.self_registration:
            return "Self-registration disabled"
        if not obj.registration_token:
            return "No token generated"
        if obj.is_token_expired():
            return "Token expired"
        if obj.token_expires_at:
            return f"Expires at {obj.token_expires_at.strftime('%Y-%m-%d %H:%M')}"
        return "No expiration set"

    def get_members_count(self, obj):
        # 1) if annotated on the group instance
        mc = getattr(obj, "members_count", None)
        if mc is not None:
            return mc

        # 2) check serializer context map prepared in the view
        group_counts = self.context.get("group_counts") or {}
        g = group_counts.get(getattr(obj, "id", None))
        if g and "members_count" in g:
            return g["members_count"]

        # 3) fallback (rare): compute directly (one query)
        from src.apps.courses.models.groups.course_enrollment import CourseEnrollment

        return CourseEnrollment.objects.filter(group=obj).count()

    def get_students_count(self, obj):
        sc = getattr(obj, "students_count", None)
        if sc is not None:
            return sc

        group_counts = self.context.get("group_counts") or {}
        g = group_counts.get(getattr(obj, "id", None))
        if g and "students_count" in g:
            return g["students_count"]

        from src.apps.courses.models.groups.course_enrollment import CourseEnrollment

        return CourseEnrollment.objects.filter(group=obj, role="student").count()

    # def get_members_count(self, obj: CourseGroup):
    #     """Get number of members"""
    #     if hasattr(obj, "members_count"):
    #         return obj.members_count
    #     return obj.members.count()
    #
    # def get_students_count(self, obj: CourseGroup):
    #     if hasattr(obj, "students_count"):
    #         return obj.students_count
    #     return obj.members.filter(role="student").count()

    def get_teachers(self, obj: CourseGroup):
        from src.api.users.serializers.users.users_list_serializer import UserListSerializer

        qs = obj.teachers  # property from model
        return UserListSerializer(qs, many=True, context=self.context).data

    @staticmethod
    def get_user_group_names(user):
        if not hasattr(user, "_cached_group_names"):
            user._cached_group_names = set(user.groups.values_list("name", flat=True))
        return user._cached_group_names
