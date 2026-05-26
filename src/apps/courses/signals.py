from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from src.apps.courses.cache import (
    invalidate_course_groups_list_cache,
    invalidate_course_groups_page_cache,
    invalidate_courses_light_list_cache,
)
from src.apps.courses.models import Course, CourseEnrollment, CourseGroup
from src.apps.users.models import User


def _course_ids_for_user(user_id: int):
    return CourseEnrollment.objects.filter(user_id=user_id).values_list("course_id", flat=True).distinct()


@receiver(pre_save, sender=CourseGroup)
def capture_previous_course_group_state(sender, instance, **kwargs) -> None:
    if not instance.pk:
        instance._previous_course_id = None
        return

    instance._previous_course_id = CourseGroup.objects.filter(pk=instance.pk).values_list(
        "course_id", flat=True
    ).first()


@receiver(post_save, sender=CourseGroup)
def invalidate_group_pages_on_group_save(sender, instance, **kwargs) -> None:
    course_ids = {instance.course_id}
    previous_course_id = getattr(instance, "_previous_course_id", None)
    if previous_course_id:
        course_ids.add(previous_course_id)

    invalidate_course_groups_list_cache()
    invalidate_course_groups_page_cache(course_ids)


@receiver(post_delete, sender=CourseGroup)
def invalidate_group_pages_on_group_delete(sender, instance, **kwargs) -> None:
    invalidate_course_groups_list_cache()
    invalidate_course_groups_page_cache([instance.course_id])


@receiver(pre_save, sender=CourseEnrollment)
def capture_previous_enrollment_state(sender, instance, **kwargs) -> None:
    if not instance.pk:
        instance._previous_course_id = None
        return

    instance._previous_course_id = CourseEnrollment.objects.filter(pk=instance.pk).values_list(
        "course_id", flat=True
    ).first()


@receiver(post_save, sender=CourseEnrollment)
def invalidate_group_pages_on_enrollment_save(sender, instance, **kwargs) -> None:
    course_ids = {instance.course_id}
    previous_course_id = getattr(instance, "_previous_course_id", None)
    if previous_course_id:
        course_ids.add(previous_course_id)

    invalidate_course_groups_list_cache()
    invalidate_course_groups_page_cache(course_ids)


@receiver(post_delete, sender=CourseEnrollment)
def invalidate_group_pages_on_enrollment_delete(sender, instance, **kwargs) -> None:
    invalidate_course_groups_list_cache()
    invalidate_course_groups_page_cache([instance.course_id])


@receiver(post_save, sender=Course)
def invalidate_course_pages_on_save(sender, instance, **kwargs) -> None:
    invalidate_courses_light_list_cache()
    invalidate_course_groups_list_cache()
    invalidate_course_groups_page_cache([instance.id])


@receiver(post_delete, sender=Course)
def invalidate_course_pages_on_delete(sender, instance, **kwargs) -> None:
    invalidate_courses_light_list_cache()
    invalidate_course_groups_list_cache()
    invalidate_course_groups_page_cache([instance.id])


@receiver(post_save, sender=User)
def invalidate_group_pages_on_user_save(sender, instance, **kwargs) -> None:
    course_ids = _course_ids_for_user(instance.id)
    if course_ids:
        invalidate_course_groups_list_cache()
        invalidate_course_groups_page_cache(course_ids)


@receiver(pre_delete, sender=User)
def capture_previous_user_courses(sender, instance, **kwargs) -> None:
    instance._previous_course_ids = list(_course_ids_for_user(instance.id))


@receiver(post_delete, sender=User)
def invalidate_group_pages_on_user_delete(sender, instance, **kwargs) -> None:
    course_ids = getattr(instance, "_previous_course_ids", [])
    if course_ids:
        invalidate_course_groups_list_cache()
        invalidate_course_groups_page_cache(course_ids)

