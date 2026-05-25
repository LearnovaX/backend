from django.db import models

from src.apps.common.models import BaseModel
from src.apps.users.models import User

from .chat_room import ChatRoom


class Message(BaseModel):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    is_read = models.BooleanField(default=False)

    file = models.FileField(upload_to="chat_files/", null=True, blank=True)

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])

    def __str__(self):
        return f"{self.sender.first_name}: {self.content[:50]}..."

    class Meta:
        db_table = "Chat_Messages"
        verbose_name = "Message"
        verbose_name_plural = "Messages"
        ordering = ("created_at",)
