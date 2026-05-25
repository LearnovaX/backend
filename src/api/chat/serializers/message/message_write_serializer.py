from rest_framework import serializers

from src.apps.chat.models import Message


class MessageWriteSerializer(serializers.ModelSerializer):
    content = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Message
        fields = ["content", "file"]

    def validate(self, attrs):
        content = (attrs.get("content") or "").strip()
        file = attrs.get("file")
        if not content and not file:
            raise serializers.ValidationError("Message must include text or a file")
        return attrs

    def create(self, validated_data):
        validated_data["sender"] = self.context["request"].user
        validated_data["chat_room"] = self.context["chat_room"]
        return super().create(validated_data)
