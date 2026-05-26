from rest_framework.serializers import ModelSerializer

from src.api.users.serializers import UserSerializer
from src.apps.notifications.models import Notification


class NotificationReadSerializer(ModelSerializer):
    receiver = UserSerializer(read_only=True)
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "title", "content", "receiver", "sender", "created_at", "updated_at"]
