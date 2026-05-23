from rest_framework import serializers

from src.apps.courses.models import Course


class CourseExportSerializer(serializers.ModelSerializer):
    author_first_name = serializers.CharField(source="author.first_name", read_only=True)
    author_last_name = serializers.CharField(source="author.last_name", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True)
    students_count = serializers.IntegerField()
    teachers_count = serializers.IntegerField()
    groups_count = serializers.IntegerField()
    tasks_count = serializers.IntegerField()

    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "description",
            "author_first_name",
            "author_last_name",
            "free_order",
            "category",
            "deadline_to_finish_course",
            "block_course_after_deadline",
            "is_certificated",
            "students_count",
            "teachers_count",
            "groups_count",
            "tasks_count",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
        }
