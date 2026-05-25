from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from src.apps.notifications.models import Notification
from src.apps.submissions.service import send_answer_status_notification


def send_realtime_status_notification(notification: Notification):
    from src.api.notifications.serializers import NotificationReadSerializer

    group_name = f"user_notifications_{notification.receiver.pk}"
    serializer = NotificationReadSerializer(instance=notification)
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        group_name, {"type": "send_answer_status_notification", "data": serializer.data}
    )


# Integration function to work with your existing notification system
def send_status_change_email_helper(notification_instance):
    """
    Helper function to extract data from notification and send email
    """
    user = notification_instance.receiver

    # Extract task info from notification title
    title_parts = notification_instance.title.split()
    task_number = None
    task_name = None

    # Parse task number and name from title
    for i, part in enumerate(title_parts):
        if part.startswith("Task") and i + 1 < len(title_parts):
            task_info = " ".join(title_parts[i + 1 :]).split(" has been")[0]
            if task_info and "." in task_info:
                number_part, name_part = task_info.split(".", 1)
                task_number = number_part.strip()
                task_name = name_part.strip()
            break

    # Determine status from notification content
    status = "have_flaws"  # default
    if "approved" in notification_instance.content.lower():
        status = "approved"
    elif "rejected" in notification_instance.content.lower():
        status = "rejected"
    elif (
        "issues" in notification_instance.content.lower()
        or "flaws" in notification_instance.content.lower()
    ):
        status = "have_flaws"

    # Send the email
    if user.email and user.first_name and task_number and task_name:
        send_answer_status_notification(
            receiver_email=user.email,
            first_name=user.first_name,
            task_name=task_name,
            task_number=task_number,
            status=status,
            feedback_text=notification_instance.feedback,
        )
