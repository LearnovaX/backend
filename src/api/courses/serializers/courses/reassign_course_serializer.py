from rest_framework import serializers

from src.apps.grades.models import Grade
from src.apps.submissions.models import Answer
from src.apps.users.models import User


class ReassignCourseSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

    def validate(self, attrs):
        user_ids = attrs.get("user_ids")
        for user_id in user_ids:
            if not User.objects.filter(pk=user_id).exists():
                raise serializers.ValidationError(f"User with id {user_id} not found")
        return attrs

    def save(self, **kwargs):
        user_ids = self.validated_data.get("user_ids")
        course = self.context.get("course")
        reassigned = 0
        for user_id in user_ids:
            user = User.objects.get(pk=user_id)
            Grade.objects.filter(answer__user=user, answer__task__course=course).delete()
            Answer.objects.filter(user=user, task__course=course).delete()
            reassigned += 1

        return reassigned
