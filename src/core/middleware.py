from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

class HealthCheckMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path == "/health/":
            return HttpResponse("ok")