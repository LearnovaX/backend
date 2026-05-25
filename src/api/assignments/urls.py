from rest_framework.routers import DefaultRouter

from src.api.assignments.views import TaskModelViewSet

router = DefaultRouter()
router.register("", TaskModelViewSet, basename="tasks")

urlpatterns = [] + router.urls
