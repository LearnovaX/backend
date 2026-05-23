from ckeditor_uploader.fields import RichTextUploadingField
from django.core.validators import FileExtensionValidator
from django.db import models

from src.apps.assignments.models.manager import ActiveTaskManager
from src.apps.common.models import BaseModel
from src.apps.common.utils import unique_image_path, validate_image_size
from src.apps.courses.models import Course
from src.apps.users.models.user import User


class Task(BaseModel):
    number = models.PositiveIntegerField(null=True, blank=True)
    name = models.CharField(max_length=100)
    description = RichTextUploadingField(blank=True)
    video = models.FileField(upload_to="task_videos/", null=True, blank=True)
    image = models.ImageField(
        upload_to=unique_image_path,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"]),
            validate_image_size,
        ],
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to="task_files/", null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="tasks")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tasks")
    enable_context_menu_for_students = models.BooleanField(default=True)
    allow_resubmitting_task = models.BooleanField(default=True)
    objects = ActiveTaskManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"{self.number}. {self.name} for {self.course.name} task"

    class Meta:
        db_table = "Tasks"
        verbose_name = "Task"
        verbose_name_plural = "Tasks"
        base_manager_name = "objects"  # TODO -> check if any errors occur
