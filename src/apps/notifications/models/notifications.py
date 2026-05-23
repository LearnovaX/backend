from django.conf import settings
from django.db import models

from src.apps.common.models import BaseModel


class Notification(BaseModel):
    title = models.CharField(max_length=100)
    content = models.TextField()
    feedback = models.TextField(null=True, blank=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
        null=True,
        blank=True,
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_notifications"
    )
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"'{self.title}' to {self.receiver.email}"

    class Meta:
        db_table = "Notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ("-created_at",)
