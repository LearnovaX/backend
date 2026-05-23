import logging
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from src.apps.users.auth.otp import create_otp_code, verify
from src.apps.users.service import send_otp_verification

logger = logging.getLogger(__name__)


class CheckTokenBeforeObtainSerializer(TokenObtainSerializer):
    otp_code = serializers.CharField(required=False, allow_blank=True)
    otp_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs: dict[str, Any]) -> dict[Any, Any]:
        super().validate(attrs)
        user = self.user
        self._check(user)

        if not getattr(user, "mfa_enabled", False):
            tokens = self._login_and_generate_tokens(user, mfa_enabled=False)
            return tokens

        token = self.initial_data.get("otp_token")
        code = self.initial_data.get("otp_code")

        if token and code:
            uid = verify(token, code)
            if uid is None:
                logger.warning(
                    f"users.login. User with id {user.pk} entered"
                    f" expired code or made too many attempts with mfa enabled status."
                )
                raise AuthenticationFailed("Code expired or too many attempts.", code="otp_expired")
            if uid is False or uid != user.id:
                logger.warning(
                    f"users.login. User with id {user.pk} entered invalid code"
                    f" with mfa enabled status."
                )
                raise AuthenticationFailed("Invalid code.", code="otp_invalid")
            tokens = self._login_and_generate_tokens(user, mfa_enabled=True)
            return tokens

        token, otp_code = create_otp_code(user_id=user.pk)

        send_otp_verification(user.email, user.first_name, otp_code)
        logger.info(f"users.login. OTP code sent for user id: {user.id}")
        return {"otp_required": True, "otp_token": token}

    @staticmethod
    def _check(user) -> None:
        if getattr(user, "must_set_password", False):
            logger.info(f"users.login. User {user.id} has no password set but attempted to login.")
            raise AuthenticationFailed(
                "You must set your password before logging in.",
                code="initial_password_required",
            )

        if not getattr(user, "email_verified", False):
            logger.info(
                f"users.login. User {user.id} has no email verified but attempted to login."
            )
            raise AuthenticationFailed(
                "Please verify your email before logging in.",
                code="email_not_verified",
            )

        if hasattr(user, "is_active") and not user.is_active:
            logger.warning(
                f"users.login. User {user.id} has deactivated account but attempted to login."
            )
            raise AuthenticationFailed("User account is disabled.", code="user_disabled")

    @staticmethod
    def _login_and_generate_tokens(user, mfa_enabled: bool):
        refresh = RefreshToken.for_user(user)
        with transaction.atomic():
            user.last_login = timezone.now()
            user.save()
        logger.info(f"users.login. Successfully logged in {user.id} with mfa status: {mfa_enabled}")
        return {"refresh": str(refresh), "access": str(refresh.access_token)}
