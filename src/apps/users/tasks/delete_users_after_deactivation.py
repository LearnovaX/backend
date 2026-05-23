import logging

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from src.apps.users.models import UserProfile

logger = logging.getLogger(__name__)


@shared_task(name="users.delete_deactivated_users")
def delete_deactivated_users():
    try:
        print("task received")
        users = UserProfile.objects.filter(
            Q(deactivation_time__lte=timezone.now()) & Q(days_to_delete_after_deactivation__lte=0)
        )
        users_count = users.count()
        # TODO move deleted users into archive.
        # users.delete()
        logger.info(f"deleted {users_count} users after deactivation")

        other_users = UserProfile.objects.filter(
            Q(deactivation_time__lte=timezone.now()) & Q(days_to_delete_after_deactivation__gt=0)
        )
        for user_profile in other_users:
            user_profile.days_to_delete_after_deactivation -= 1
            user_profile.save()
    except Exception as e:
        logger.critical(msg=e)
