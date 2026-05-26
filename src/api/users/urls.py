from django.urls import include, path
from rest_framework.routers import DefaultRouter

from src.api.users.views import (
    AdminUserModelViewSet,
    AuthViewSet,
    CheckTokenBeforeObtainView,
    CompleteGoogleRegistration,
    CustomTokenRefreshView,
    GoogleCallBackView,
    GoogleLoginView,
    SetInitialPasswordView,
    UserViewSet,
    ValidateInviteView,
)

router = DefaultRouter()
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"user", UserViewSet, basename="user")
router.register("user-management", AdminUserModelViewSet, basename="admin-users")

app_name = "users"
urlpatterns = [
    path("login/", CheckTokenBeforeObtainView.as_view(), name="login"),
    path("login/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("login/google/", GoogleLoginView.as_view(), name="google_login"),
    path("login/google/callback/", GoogleCallBackView.as_view(), name="google_callback"),
    path("set-initial-password/", SetInitialPasswordView.as_view(), name="set_initial_password"),
    path("validate-invite/", ValidateInviteView.as_view(), name="validate_invite"),
    path(
        "login/google/complete-profile/",
        CompleteGoogleRegistration.as_view(),
        name="complete_google_registration",
    ),
    path("", include(router.urls)),
]
