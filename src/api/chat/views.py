from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from src.apps.chat.models import ChatRoom, Message

from .serializers import (
    ChatRoomReadSerializer,
    ChatRoomWriteSerializer,
    MessageReadSerializer,
    MessageWriteSerializer,
)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@extend_schema(tags=["Chat Rooms"])
class ChatRoomModelViewSet(ModelViewSet):
    """
    ViewSet for managing chat rooms.
    Only shows chat rooms where current user is either teacher or student.
    """

    def get_queryset(self):
        user = self.request.user
        return (
            ChatRoom.objects.filter(Q(teacher=user) | Q(student=user))
            .select_related("student", "teacher", "course")
            .prefetch_related("messages")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return ChatRoomWriteSerializer
        return ChatRoomReadSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset().order_by("-updated_at")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chat_room = serializer.save()

        response_serializer = ChatRoomReadSerializer(chat_room, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(
        self,
        request,
        *args,
        pk=None,
        **kwargs,
    ):
        chat_room = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = self.get_serializer(chat_room)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def mark_as_read(self, request, pk=None):
        chat_room = get_object_or_404(self.get_queryset(), pk=pk)

        unread_messages = chat_room.messages.filter(~Q(sender=request.user), is_read=False)
        unread_messages.update(is_read=True)
        return Response({"message": f"Marked {unread_messages.count()} messages as read."})


@extend_schema(tags=["Chat Messages"])
class MessageModelViewSet(ModelViewSet):
    serializer_class = MessageReadSerializer

    def get_queryset(self):
        user = self.request.user

        # Check if filtering by chat room
        room_id = self.kwargs.get("room_id") or self.request.query_params.get("room_id")

        base_queryset = Message.objects.filter(
            Q(chat_room__teacher=user) | Q(chat_room__student=user)
        ).select_related("sender", "chat_room")

        if room_id:
            base_queryset = base_queryset.filter(chat_room_id=room_id)

        return base_queryset

    def get_serializer_class(self):
        if self.action == "create":
            return MessageWriteSerializer
        return MessageReadSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()

        # Handle both nested route and query parameter
        room_id = self.kwargs.get("room_id") or self.request.data.get("chat_room_id")

        if room_id:
            try:
                chat_room = ChatRoom.objects.get(
                    Q(teacher=self.request.user) | Q(student=self.request.user),
                    pk=room_id,
                    is_active=True,
                )
                context["chat_room"] = chat_room
            except ChatRoom.DoesNotExist:
                pass  # Will be handled in validation

        return context

    def create(self, request, *args, **kwargs):
        """Send a new message"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Validate chat room access
        if "chat_room" not in serializer.context:
            return Response(
                {"error": "Invalid chat room or no access"}, status=status.HTTP_400_BAD_REQUEST
            )

        message = serializer.save()

        # Update chat room's updated_at timestamp
        message.chat_room.save(update_fields=["updated_at"])

        # Notify WebSocket subscribers for realtime updates (including file messages)
        self._broadcast_message(message)

        # Return the created message with full details
        response_serializer = MessageReadSerializer(message, context=self.get_serializer_context())
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def _broadcast_message(self, message: Message):
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        async_to_sync(channel_layer.group_send)(
            f"chat_room_{message.chat_room_id}",
            {
                "type": "chat_message",
                "message_id": message.id,
                "sender_id": message.sender_id,
            },
        )
