# Simplified chat/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChatRoomModelViewSet, MessageModelViewSet

router = DefaultRouter()
router.register("rooms", ChatRoomModelViewSet, basename="chatroom")
router.register("messages", MessageModelViewSet, basename="message")

urlpatterns = [
    path("", include(router.urls)),
    # Custom endpoints if needed
    path(
        "rooms/<int:room_id>/messages/",
        MessageModelViewSet.as_view({"get": "list", "post": "create"}),
        name="room-messages",
    ),
]

# This gives you:
# GET/POST /api/chat/rooms/ - List/Create chat rooms
# GET/PUT/DELETE /api/chat/rooms/{id}/ - Room detail operations
# GET/POST /api/chat/messages/ - List/Create messages (with room filtering)
# GET/PUT/DELETE /api/chat/messages/{id}/ - Message operations
# GET/POST /api/chat/rooms/{room_id}/messages/ - Room-specific messages
