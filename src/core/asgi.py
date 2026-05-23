import os

from django import setup  # noqa: E402

from src.core.observability.tracing import setup_tracing  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.core.settings")
setup()
setup_tracing()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from src.api.notifications import routing as notification_routing  # noqa: E402
from src.apps.common.middleware import JWTAuthMiddleware  # noqa: E402

websocket_patterns = [
    *notification_routing.websocket_urlpatterns,
]
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": JWTAuthMiddleware(URLRouter(websocket_patterns)),
    }
)
