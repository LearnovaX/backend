from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import PlagiarismDashboardView, PlagiarismReportViewSet

router = DefaultRouter()
router.register("reports", PlagiarismReportViewSet, basename="plagiarism-reports")

urlpatterns = [
    path("dashboard/", PlagiarismDashboardView.as_view(), name="plagiarism-dashboard"),
]
urlpatterns += router.urls
