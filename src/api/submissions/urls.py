from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AnswerFileViewSet, AnswerModelViewSet

router = DefaultRouter()
router.register("", AnswerModelViewSet, basename="answers")
router.register("answer-files", AnswerFileViewSet, basename="answer-file")

urlpatterns = [
    path("", include(router.urls)),
]
