from rest_framework.serializers import ModelSerializer

from src.apps.notifications.models import Notification


class NotificationWriteSerializer(ModelSerializer):
    class Meta:
        model = Notification
        fields = ["title", "content", "receiver", "sender"]
