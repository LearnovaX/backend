from rest_framework import serializers

from src.api.users.serializers import AllUsersSerializerLight
from src.apps.courses.models.groups import CourseEnrollment


class CourseStudentsInfoSerializer(serializers.ModelSerializer):
    user = AllUsersSerializerLight(read_only=True)
    group = serializers.SerializerMethodField()
    points = serializers.SerializerMethodField()
    course_status = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    started_at = serializers.SerializerMethodField()
    course_id = serializers.IntegerField(source="course.pk", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    finished_at = serializers.SerializerMethodField()

    class Meta:
        model = CourseEnrollment
        fields = [
            "id",
            "user",
            "group",
            "role",
            "enrolled_date",
            "points",
            "course_status",
            "progress",
            "finished_at",
            "started_at",
            "course_id",
            "course_name",
        ]

    def get_group(self, obj: CourseEnrollment) -> dict:
        return {
            "id": obj.group.pk,
            "name": obj.group.name,
        }

    def get_points(self, obj) -> float | int:
        return 0

    def get_course_status(self, obj: CourseEnrollment) -> str:
        return "in_progress"  # 'finished', 'not_started'

    def get_progress(self, obj: CourseEnrollment) -> float:
        return 0.0

    def get_started_at(self, obj: CourseEnrollment):
        return obj.enrolled_date

    def get_finished_at(self, obj: CourseEnrollment):
        return obj.enrolled_date
