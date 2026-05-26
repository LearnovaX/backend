from rest_framework import serializers

from src.apps.courses.models import CourseGroup


class CourseGroupReadLightSerializer(serializers.ModelSerializer):
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseGroup
        fields = [
            "id",
            "name",
            "course",
            "members_count",
        ]

    def get_members_count(self, obj: CourseGroup):
        """Get number of members"""
        if hasattr(obj, "members_count"):
            return obj.members_count
        return obj.members.count()
