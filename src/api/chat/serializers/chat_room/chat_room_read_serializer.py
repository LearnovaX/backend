from django.db.models import Q
from rest_framework import serializers

from src.api.chat.serializers.message.message_read_serializer import MessageReadSerializer
from src.api.users.serializers import UserSerializer
from src.apps.chat.models import ChatRoom


class ChatRoomReadSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "teacher",
            "student",
            "course",
            "is_active",
            "last_message",
            "unread_count",
            "other_user",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_last_message(self, obj: ChatRoom):
        last_message = obj.messages.last()
        return (
            MessageReadSerializer(last_message, context=self.context).data if last_message else None
        )

    def get_unread_count(self, obj: ChatRoom):
        current_user = self.context["request"].user
        return obj.messages.filter(~Q(sender=current_user), is_read=False).count()

    def get_other_user(self, obj: ChatRoom):
        current_user = self.context["request"].user
        other_user = obj.get_other_user(current_user)
        return UserSerializer(other_user).data
