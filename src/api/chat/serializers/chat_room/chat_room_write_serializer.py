from django.db.models import Q
from rest_framework import serializers

from src.apps.chat.models import ChatRoom
from src.apps.courses.models import CourseEnrollment
from src.apps.users.models import User


class ChatRoomWriteSerializer(serializers.ModelSerializer):
    other_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ChatRoom
        fields = ["other_user_id", "course"]

    def validate_other_user_id(self, value):
        current_user = self.context["request"].user

        try:
            other_user = User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        if other_user == current_user:
            raise serializers.ValidationError("Cannot create chat with yourself")

        self._validate_chat_permission(current_user, other_user)

        return value

    def _validate_chat_permission(self, user1, user2):
        """Check if two users can chat (must be teacher-student)"""
        can_chat = CourseEnrollment.objects.filter(
            Q(
                user=user2,
                role="teacher",
                course__enrollments__user=user1,
                course__enrollments__role="student",
            )
            | Q(
                user=user1,
                role="teacher",
                course__enrollments__user=user2,
                course__enrollments__role="student",
            )
        ).exists()
        if not can_chat:
            raise serializers.ValidationError(
                "Chat is only allowed to chat between teacher and their students"
            )

    def create(self, validated_data):
        current_user = self.context["request"].user
        other_user_id = validated_data.pop("other_user_id")
        other_user = User.objects.get(pk=other_user_id)

        current_user_is_teacher = CourseEnrollment.objects.filter(
            user=current_user,
            role="teacher",
        ).exists()

        if current_user_is_teacher:
            teacher, student = current_user, other_user
        else:
            teacher, student = other_user, current_user

        chat_room, _ = ChatRoom.objects.get_or_create(
            teacher=teacher, student=student, defaults=validated_data
        )
        return chat_room
