from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GradeModelViewSet

router = DefaultRouter()
router.register("", GradeModelViewSet, basename="grades")
urlpatterns = [
    path("", include(router.urls)),
]
