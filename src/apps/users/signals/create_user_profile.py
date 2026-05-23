import logging

from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver

from src.apps.users.models import User, UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance: User, created, **kwargs):
    if kwargs.get("raw"):
        return

    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
            name = {
                "admin": "Admins",
                "teacher": "Teachers",
                "assistant": "Assistants",
                "manager": "Managers",
                "student": "Students",
            }.get(instance.role, "Students")
            if name in instance.groups.values_list("name", flat=True):
                return
            group, _ = Group.objects.get_or_create(name=name)
            instance.groups.add(group)

        except IntegrityError as e:
            logger.warning(
                "users.profile. Failed to create profile for user=%s error=%s",
                instance.pk,
                e,
            )
