# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from channels.layers import get_channel_layer
# from asgiref.sync import async_to_sync
# from .models import Notification
# from src.api.notifications.serializers import NotificationReadSerializer
#
#
# @receiver(post_save, sender=Notification)
# def answer_status_notification(sender, instance: Notification, created, **kwargs):
#     """Send update when notification is created"""
#     user_id = instance.receiver.pk
#     group_name = f'user_notifications_{user_id}'
#     serializer = NotificationReadSerializer(instance=instance)
#     channel_layer = get_channel_layer()
#
#     async_to_sync(channel_layer.group_send)(
#         group_name,
#         {
#             'type': 'send_answer_status_notification',
#             'data': serializer.data
#         }
#     )
