from rest_framework import serializers

from src.api.users.serializers import UserSerializer
from src.apps.chat.models import Message


class MessageReadSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    chat_room_id = serializers.IntegerField(read_only=True)
    is_my_message = serializers.SerializerMethodField()
    message_direction = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "chat_room_id",
            "content",
            "sender",
            "file",
            "is_read",
            "created_at",
            "updated_at",
            "is_my_message",
            "message_direction",
        ]

    def get_is_my_message(self, obj):
        """Check if current user is the sender"""
        request = self.context.get("request")
        if request and request.user:
            return obj.sender_id == request.user.id
        return False

    def get_message_direction(self, obj):
        """Return 'sent' or 'received' based on current user"""
        request = self.context.get("request")
        if request and request.user:
            return "sent" if obj.sender_id == request.user.id else "received"
        return "unknown"
