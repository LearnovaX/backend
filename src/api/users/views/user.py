import logging

import requests

# from secrets import token_urlsafe
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenViewBase

from src.api.users.serializers import (
    CheckTokenBeforeObtainSerializer,
    ConfirmEmailChangeSerializer,
    CustomTokenRefreshSerializer,
    ForgotPasswordSerializer,
    LogoutSerializer,
    RegisterSerializer,
    RequestEmailChangeSerializer,
    ResetPasswordSerializer,
    SetInitialPasswordSerializer,
    UserProfileReadSerializer,
    UserProfileWriteSerializer,
    UserSerializer,
    ValidateInviteSerializer,
    VerifyPasswordResetSerializer,
    VerifyRegisterSerializer,
)
from src.apps.common.utils import generate_random_code
from src.apps.users.models import CodeEmail, CodePassword, TemporaryUser, User, UserProfile
from src.apps.users.service import (
    send_email_verification,
    send_password_verification,
)

logger = logging.getLogger(__name__)


@extend_schema(tags=["Auth"])
class AuthViewSet(viewsets.GenericViewSet):
    """
    ViewSet for authentication related operations
    """

    def get_serializer_class(self):
        if self.action == "register":
            return RegisterSerializer
        elif self.action == "verify_registration":
            return VerifyRegisterSerializer
        elif self.action == "forgot_password":
            return ForgotPasswordSerializer
        elif self.action == "verify_password_reset":
            return VerifyPasswordResetSerializer
        elif self.action == "reset_password":
            return ResetPasswordSerializer
        elif self.action == "logout":
            return LogoutSerializer
        return RegisterSerializer

    def get_permissions(self):
        if self.action in ["logout", "logout_of_all_devices"]:
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def register(self, request):
        """
        Register a new user and send verification email
        """
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.validated_data.pop("re_password", None)
            email = serializer.validated_data.get("email")
            TemporaryUser.objects.filter(email=email).delete()
            TemporaryUser.objects.create(
                **serializer.validated_data, re_password=request.data.get("re_password")
            )

            code = generate_random_code()
            CodeEmail.objects.update_or_create(email=email, code=code)
            send_email_verification(email, serializer.validated_data.get("first_name"), code)
            return Response(
                {
                    "message": "Verification code sent to your email. Please verify to"
                    " complete registration.",
                    "email": email,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def verify_registration(self, request):
        """
        Verify registration with email code
        """
        verify_serializer = self.get_serializer(data=request.data)
        verify_serializer.is_valid(raise_exception=True)

        email = verify_serializer.validated_data.get("email")

        pending_user_data = TemporaryUser.objects.filter(email=email).values().first()
        if not pending_user_data:
            return Response(
                {"message": "No pending registration found. Please start registration again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            serializer = RegisterSerializer(data=pending_user_data)
            if serializer.is_valid():
                user = serializer.save()

                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "message": "Registration completed successfully",
                        "user": UserSerializer(user).data,
                        "tokens": {
                            "refresh": str(refresh),
                            "access": str(refresh.access_token),
                        },
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": "Error creating user", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"message": f"Error creating user: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def forgot_password(self, request):
        """
        Request password reset code
        """
        logger.info("users.forgot_password. Request forgot password start.")
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data["email"]
            user = User.objects.get(email=email)  # We know it exists from validation

            code = generate_random_code()

            CodePassword.objects.update_or_create(user=user, code=code)

            send_password_verification(email, user.first_name, code)
            logger.info("users.forgot_password. Email sent.")
            return Response(
                {
                    "message": "Password reset code has been sent to your email.",
                    "email": email,
                },
                status=status.HTTP_200_OK,
            )
        logger.warning(f"users.forgot_password. bad request: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def verify_password_reset(self, request):
        """
        Verify password reset code
        """
        logger.info("users.verify_password_reset. verify code for forgot password start.")
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(f"users.verify_password_reset. bad request: {serializer.errors}")
            return Response(
                {"message": f"Error verifying password reset code: {serializer.errors}"},
            )

        email = serializer.validated_data.get("email")

        user = User.objects.filter(email=email).first()
        if not user:
            logger.warning("users.verify_password_reset. no user found.")
            return Response({"message": f"User with {email} not found."})

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        logger.info("users.verify_password_reset. tokens sent.")
        return Response(
            {
                "message": "Code verified successfully. You can now reset your password.",
                "uid": uid,
                "token": token,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def reset_password(self, request):
        """
        Reset password with token
        """
        logger.info("users.reset_password... reset password start.")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"users.reset_password... bad request, error: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        uidb64 = serializer.validated_data.get("uid")
        token = serializer.validated_data.get("token")
        new_password = serializer.validated_data.get("new_password")

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            logger.warning("users.reset_password... user provided invalid uid.")
            return Response({"message": "Invalid user."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            logger.warning("users.reset_password... user provided invalid token.")
            return Response(
                {"message": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.must_set_password = False
        user.email_verified = True
        user.save()
        CodePassword.objects.filter(user=user).delete()
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)

        logger.info("users.reset_password... reset password complete for user id=%s", user.pk)
        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["delete"])
    @transaction.atomic
    def logout(self, request):
        """
        Logout user by blacklisting refresh token,
        "refresh_token" parameter is required
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info("users.logout. user id=%s", self.request.user.pk)
        return Response({"message": "Logout successful."}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["delete"], url_path="logout-of-all-devices")
    @transaction.atomic
    def logout_of_all_devices(self, request):
        user = request.user
        tokens = OutstandingToken.objects.filter(user=user)
        i = 0
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
            i += 1
        logger.info(f"users.logout-of-all-devices. User logged out of {i} devices.")
        return Response(
            {"message": f"Successfully logged out of {i} devices."},
            status=status.HTTP_204_NO_CONTENT,
        )


@extend_schema(tags=["User"])
class UserViewSet(viewsets.GenericViewSet):
    """
    ViewSet for user profile operations
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "update_profile":
            return UserProfileWriteSerializer
        elif self.action == "profile":
            return UserProfileReadSerializer
        elif self.action == "request_email_change":
            return RequestEmailChangeSerializer
        elif self.action == "confirm_email_change":
            return ConfirmEmailChangeSerializer
        return UserSerializer

    @action(detail=False, methods=["get"])
    def profile(self, request):
        """
        Get current user profile
        """
        user = request.user
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            logger.warning("users.profile. UserProfile DoesNotExist")
            return Response({"message": "User has no profile."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    @extend_schema(responses=UserProfileReadSerializer)
    @action(
        detail=False,
        methods=["put", "patch"],
        parser_classes=(MultiPartParser, FormParser, JSONParser),
    )
    @transaction.atomic
    def update_profile(self, request):
        """
        Update current user profile, email is user to update, and email will not be updated.
        """

        profile = get_object_or_404(UserProfile, user=request.user)

        serializer = self.get_serializer(
            instance=profile,
            data=request.data,
            partial=(request.method == "PATCH"),
        )

        if not serializer.is_valid():
            logger.warning(
                f"users.update_profile. User profile update failed. error={serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        instance = serializer.save()
        response = UserProfileReadSerializer(instance, context=self.get_serializer_context())
        logger.info(f"users.update_profile. User with id {request.user.pk} updated profile.")
        return Response(response.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def request_email_change(self, request):
        """
        Request email change verification
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"users.request_email_change. Bad request. error={serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        new_email = serializer.validated_data.get("new_email")
        logger.info(
            f"users.request_email_change. New email requested: {new_email} "
            f"for user id {request.user.pk}"
        )
        return Response({"message": f"Successfully sent verification code to {new_email}"})

    @action(detail=False, methods=["post"])
    @transaction.atomic
    def confirm_email_change(self, request):
        """
        Confirm email change with verification code
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"users.confirm_email_change. Bad request. error={serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            f"users.confirm_email_change. Confirm email change successful "
            f"for user id {request.user.pk}"
        )
        return Response({"message": "Successfully changed to new email"})

    @action(detail=False, methods=["delete"])
    @transaction.atomic
    def delete_account(self, request):
        """
        Delete current user account
        """
        user = request.user
        user.delete()
        logger.info(f"users.delete_account. User with id {request.user.pk} deleted account.")
        return Response(
            {"message": "Account deletion was successful."}, status=status.HTTP_204_NO_CONTENT
        )


@extend_schema(tags=["Google Login"])
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # state = token_urlsafe(24)
        auth_url = (
            f"{settings.env.str('GOOGLE_AUTH_URL')}"
            f"?client_id={settings.env.str('GOOGLE_CLIENT_ID')}"
            f"&redirect_uri={settings.env.str('GOOGLE_REDIRECT_URI')}"
            f"&response_type=code"
            f"&scope=openid email profile"
            # f"&state={state}"
        )

        return redirect(auth_url)


@extend_schema(tags=["Google Login"])
class GoogleCallBackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.GET.get("code")
        token_data = {
            "code": code,
            "client_id": settings.env.str("GOOGLE_CLIENT_ID"),
            "client_secret": settings.env.str("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": settings.env.str("GOOGLE_REDIRECT_URI"),
            "grant_type": "authorization_code",
        }

        token_response = requests.post(settings.env.str("GOOGLE_TOKEN_URL"), data=token_data)
        token_json = token_response.json()
        access_token = token_json.get("access_token")

        user_info_response = requests.get(
            settings.env.str("GOOGLE_USER_INFO_URL"),
            headers={"Authorization": f"Bearer {access_token}"},
        )

        user_info = user_info_response.json()

        google_user_id = user_info.get("sub")
        first_name = user_info.get("name", None)
        last_name = user_info.get("given_name", None)
        email = user_info.get("email")

        if User.objects.filter(email=email, google_id__isnull=True).exists():
            return Response({"You already in the system. Please login in a standard way."})

        user, created = User.objects.get_or_create(
            google_id=google_user_id,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
        )

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        if created:
            user.set_unusable_password()
            user.save()

            frontend_url = settings.env.str("FRONTEND_URL", default="http://localhost:8080")
            redirect_url = (
                f"{frontend_url}/register/complete-profile?access_token={str(access)}"
                f"&refresh_token={str(refresh)}&email={email}&message=Registration "
                f"completed successfully"
            )
            return redirect(redirect_url)

        frontend_url = settings.env.str("FRONTEND_URL", default="http://localhost:8080")
        redirect_url = (
            f"{frontend_url}/oauth/google/callback?access_token={access}"
            f"&refresh_token={refresh}&email={email}"
        )
        return redirect(redirect_url)


@extend_schema(tags=["Google Login"])
class CompleteGoogleRegistration(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        role = request.data.get("role")
        region = request.data.get("region")
        phone_number = request.data.get("phone_number")
        email = request.data.get("email")
        user = User.objects.filter(email=email).first()

        if not user:
            return Response(f"User with {email} email not found.", status=status.HTTP_404_NOT_FOUND)
        if User.objects.filter(phone_number=phone_number).exists():
            return Response({"message": f"User with {phone_number} phone number already exists."})

        user.region = region
        user.phone_number = phone_number
        if role and role == "Farmers":
            user_group, _ = Group.objects.get_or_create(name="Farmers")
        elif role and role == "Exporters":
            user_group, _ = Group.objects.get_or_create(name="Exporters")
        elif role and role == "Analysts":
            user_group, _ = Group.objects.get_or_create(name="Analysts")
        else:
            user_group, _ = Group.objects.get_or_create(name="Users")
        user.groups.clear()
        user.groups.add(user_group)
        user.save()
        return Response(
            {
                "message": "User profile updated successfully",
                "role": role,
                "region": region,
            }
        )


@extend_schema(tags=["Auth"], request=SetInitialPasswordSerializer)
class SetInitialPasswordView(APIView):
    """
    Response format:
    "message": "success",
    "tokens": {
        "refresh": "token",
        "access": "token"
    }
    """

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = SetInitialPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                f"users.SetInitialPassword. Bad request: "
                f"{serializer.errors} for user id {request.user.pk}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        logger.info(
            f"users.SetInitialPassword. Initial password for user id {user.pk} set successfully"
        )
        return Response(
            {
                "message": "Password set successfully. You can now log in.",
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Auth"], request=ValidateInviteSerializer)
class ValidateInviteView(APIView):
    """
    Response format:
    "valid": boolean,
    "errors": "errors"
    """

    permission_classes = [AllowAny]

    def post(self, request):
        s = ValidateInviteSerializer(data=request.query_params)
        logger.info("users.ValidateInvite. requested.")
        if s.is_valid():
            return Response({"valid": True})
        return Response({"valid": False, "errors": s.errors}, status=200)
        # return Response({"valid": False, "errors": s.errors}, status=400)


@extend_schema(tags=["Auth"])
class CheckTokenBeforeObtainView(TokenViewBase):
    permission_classes = [AllowAny]
    serializer_class = CheckTokenBeforeObtainSerializer


@extend_schema(tags=["Auth"])
class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer
