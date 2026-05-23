from django.db.models import Max
from rest_framework import serializers

from src.apps.courses.models import CourseEnrollment
from src.apps.submissions.models import Answer
from src.apps.users.models import User


class TeacherStudentsSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.pk")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.CharField(source="user.email")
    profile_photo = serializers.SerializerMethodField()
    to_check_count = serializers.SerializerMethodField()
    group_id = serializers.IntegerField(source="group.pk")
    group_name = serializers.CharField(source="group.name")
    course_id = serializers.IntegerField(source="course.pk")
    course_name = serializers.CharField(source="course.name")
    last_updated_at = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_id",
            "first_name",
            "last_name",
            "email",
            "profile_photo",
            "to_check_count",
            "group_id",
            "group_name",
            "course_id",
            "course_name",
            "last_updated_at",
        ]

    def get_to_check_count(self, obj: CourseEnrollment):
        return Answer.objects.filter(
            user=obj.user, task__course=obj.course, status=Answer.Status.in_review
        ).count()

    def get_profile_photo(self, obj: CourseEnrollment):
        prof = getattr(obj.user, "profile", None)
        img = getattr(prof, "profile_photo", None)
        if not img:
            return None
        url = img.url
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_last_updated_at(self, obj: CourseEnrollment):
        return Answer.objects.filter(user=obj.user, task__course=obj.course).aggregate(
            last_updated_at=Max("updated_at")
        )["last_updated_at"]
