from rest_framework import serializers

from src.apps.assignments.models import Task
from src.apps.grades.models import Grade
from src.apps.submissions.models import Answer
from src.apps.users.models import User


class ReassignTaskToUserSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    user_id = serializers.IntegerField()

    def validate(self, attrs):
        user_id = attrs.get("user_id")
        task_id = attrs.get("task_id")

        user = User.objects.filter(id=user_id).first()

        if not user:
            raise serializers.ValidationError(f"User not found with id {user_id}")

        task = Task.objects.filter(id=task_id).first()

        if not task:
            raise serializers.ValidationError(f"Task not found with id {task_id}")

        Grade.objects.filter(answer__task=task, answer__user=user).delete()
        Answer.objects.filter(task=task_id, user=user).delete()

        return attrs
