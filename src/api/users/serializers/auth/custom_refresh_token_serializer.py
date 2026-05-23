from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from src.apps.users.models import User


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            refresh = RefreshToken(attrs["refresh"])
            user_id = refresh["user_id"]
        except Exception:
            raise InvalidToken("Invalid refresh token")

        user = User.objects.filter(pk=user_id).first()
        if not user:
            raise InvalidToken("User not found")

        if not user.is_active:
            raise InvalidToken("User is disabled")

        if not getattr(user, "email_verified", False):
            raise InvalidToken("Email not verified")

        if getattr(user, "must_set_password", False):
            raise InvalidToken("User must set password")

        data = super().validate(attrs)

        return data
