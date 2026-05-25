from django.urls import include, path
from rest_framework.routers import DefaultRouter

from src.api.courses.views import (
    AllUsersViewSet,
    CategoryModelViewSet,
    CourseEnrollmentViewSet,
    CourseGroupViewSet,
    CourseViewSet,
)

router = DefaultRouter()
router.register("courses", CourseViewSet, basename="courses")
router.register("groups", CourseGroupViewSet, basename="courses-groups")
router.register("enrollments", CourseEnrollmentViewSet, basename="courses-enrollments")
router.register("categories", CategoryModelViewSet, basename="courses-categories")
router.register("all-users", AllUsersViewSet, basename="all-users")

urlpatterns = [
    path("", include(router.urls)),
]
