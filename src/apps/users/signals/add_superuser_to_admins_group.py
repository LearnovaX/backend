import logging

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from src.apps.users.models import User

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def add_superuser_to_admins_group(sender, instance, created, **kwargs):
    if created and instance.is_superuser:
        try:
            admins_group, _ = Group.objects.get_or_create(name="Admins")
            instance.groups.add(admins_group)
        except Exception as e:
            logger.critical(msg=e)
