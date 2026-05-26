"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Import admin customizations
import src.core.admin  # noqa

from src.core.observability.metrics import metrics_view

def health(request):
    return HttpResponse("ok")


urlpatterns = [
    path("api/", include("src.api.urls")),
    path("health/", health, name="health"),
    path("metrics/", metrics_view, name="metrics"),
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/silk/", include("silk.urls", namespace="silk")),
    path("api/admin/", admin.site.urls),
    path("api/ckeditor/", include("ckeditor_uploader.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
