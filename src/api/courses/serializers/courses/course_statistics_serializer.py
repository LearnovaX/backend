from rest_framework import serializers


class CourseStatisticsSerializer(serializers.Serializer):
    course_id = serializers.IntegerField(source="pk")
    students_count = serializers.IntegerField()
    teachers_count = serializers.IntegerField()
    groups_count = serializers.IntegerField()
    tasks_count = serializers.IntegerField()
