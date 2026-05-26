import logging

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    def validate(self, attrs):
        refresh_token = attrs.get("refresh_token")
        if not refresh_token:
            logger.warning("users.logout. User did not provide refresh token")
            raise serializers.ValidationError("refresh_token is required")

        try:
            token = RefreshToken(refresh_token)
        except Exception as e:
            logger.warning("users.logout. Invalid refresh token: %s", e)
            raise serializers.ValidationError("Invalid refresh token")

        request_user_id = self.context["request"].user.pk
        token_user_id = token["user_id"]
        if token_user_id and request_user_id and (str(token_user_id) != str(request_user_id)):
            logger.warning(
                "users.logout. Refresh token does not belong to user id=%s", request_user_id
            )
            raise serializers.ValidationError("This refresh token does not belong to you")

        token.blacklist()
        return attrs
