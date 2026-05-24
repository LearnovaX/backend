import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q

from src.api.chat.serializers import MessageReadSerializer
from src.apps.chat.models import ChatRoom, Message


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat functionality.
    Each connection joins a specific chat room.
    """

    async def connect(self):
        self.chat_room_id = self.scope["url_route"]["kwargs"]["chat_room_id"]
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated or isinstance(self.user, AnonymousUser):
            await self.close()
            return

        has_access = await self.check_chat_room_access()
        if not has_access:
            print("Access denied")
            await self.close()
            return

        self.room_group_name = f"chat_room_{self.chat_room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send_recent_messages()

    async def disconnect(self, code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "send_message":
                await self.handle_send_message(data)
            elif message_type == "mark_as_read":
                await self.handle_mark_as_read(data)
            elif message_type == "typing":
                await self.handle_typing(data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.send_error(str(e))

    async def handle_send_message(self, data):
        """Handle sending a new chat message"""
        content = data.get("content", "").strip()
        if not content:
            await self.send_error("Invalid message. Message content can't be empty")
            return

        message = await self.create_message(content)
        if message:
            # Send to all users in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "chat_message", "message_id": message.id, "sender_id": message.sender.id},
            )

    async def handle_mark_as_read(self, data):
        message_id = data.get("message_id")
        if message_id:
            success = await self.mark_message_as_read(message_id)
            if success:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "message_read", "message_id": message_id, "read_by": self.user.id},
                )

    async def handle_typing(self, data):
        """Handle typing indicator"""
        is_typing = data.get("is_typing", False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_status",
                "user_id": self.user.id,
                "user_name": f"{self.user.first_name} {self.user.last_name}",
                "is_typing": is_typing,
            },
        )

    async def chat_message(self, event):
        """Send chat message to WebSocket with proper context for current user"""
        message = await self.get_message_by_id(event["message_id"])
        if message:
            # Serialize with current user context (same as REST API)
            message_data = await self.serialize_message_for_user(message, self.user)
            await self.send(text_data=json.dumps({"type": "message", "data": message_data}))

    async def message_read(self, event):
        """Send message read notification to WebSocket"""
        if event["read_by"] != self.user.id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "message_read",
                        "message_id": event["message_id"],
                    }
                )
            )

    async def typing_status(self, event):
        """Send typing status to WebSocket"""
        if event["user_id"] != self.user.id:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "typing",
                        "user_id": event["user_id"],
                        "user_name": event["user_name"],
                        "is_typing": event["is_typing"],
                    }
                )
            )

    @database_sync_to_async
    def check_chat_room_access(self):
        try:
            ChatRoom.objects.get(
                Q(teacher=self.user) | Q(student=self.user), id=self.chat_room_id, is_active=True
            )
            return True
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def create_message(self, content):
        """Create a new message in the database"""
        try:
            chat_room = ChatRoom.objects.get(
                Q(teacher=self.user) | Q(student=self.user), pk=self.chat_room_id, is_active=True
            )
            message = Message.objects.create(
                chat_room=chat_room,
                content=content,
                sender=self.user,
            )
            chat_room.save(update_fields=["updated_at"])
            return message
        except ChatRoom.DoesNotExist:
            return None
        except Exception as e:
            print(f"Error creating message: {e}")
            return None

    @database_sync_to_async
    def get_message_by_id(self, message_id):
        """Get message by ID"""
        try:
            return Message.objects.select_related("sender").get(id=message_id)
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def serialize_message_for_user(self, message, user):
        """Serialize message with user context (same as REST API)"""
        from django.http import HttpRequest

        # Create mock request for serializer context
        request = HttpRequest()
        request.user = user

        serializer = MessageReadSerializer(message, context={"request": request})
        return serializer.data

    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mark a message as read"""
        try:
            message = Message.objects.get(id=message_id, chat_room_id=self.chat_room_id)
            # Only allow marking others' messages as read
            if message.sender != self.user:
                message.mark_as_read()
                return True
            return False
        except Message.DoesNotExist:
            return False

    @database_sync_to_async
    def get_recent_messages(self, limit=20):
        """Get recent messages for the chat room"""
        try:
            chat_room = ChatRoom.objects.get(id=self.chat_room_id)
            messages = (
                Message.objects.filter(chat_room=chat_room)
                .select_related("sender")
                .order_by("-created_at")[:limit]
            )

            # Return in chronological order
            return list(reversed(messages))
        except ChatRoom.DoesNotExist:
            return []

    async def send_recent_messages(self):
        """Send recent messages when user connects"""
        messages = await self.get_recent_messages()
        for message in messages:
            message_data = await self.serialize_message_for_user(message, self.user)
            await self.send(text_data=json.dumps({"type": "message", "data": message_data}))

    async def send_error(self, error_message):
        """Send error message to WebSocket"""
        await self.send(text_data=json.dumps({"type": "error", "message": error_message}))
