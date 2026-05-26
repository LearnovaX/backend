from django.core.validators import FileExtensionValidator
from django.db import models

from src.apps.common.models import BaseModel
from src.apps.common.utils import unique_image_path, validate_image_size
from src.apps.courses.models import Category
from src.apps.users.models import User

from .manager import ActiveCourseManager


class Course(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="courses", null=True, blank=True
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_courses", null=True, blank=True
    )
    image = models.ImageField(
        upload_to=unique_image_path,
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"]),
            validate_image_size,
        ],
    )

    deadline_to_finish_course = models.DateTimeField(
        null=True, blank=True, verbose_name="Deadline to finish course"
    )

    block_course_after_deadline = models.BooleanField(default=False)
    is_certificated = models.BooleanField(default=True)
    free_order = models.BooleanField(default=True)
    allow_teachers_to_manage_tasks = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = ActiveCourseManager()

    def __str__(self):
        return f"{self.name} - {self.description[:50]}..."

    class Meta:
        db_table = "Courses"
        verbose_name = "Course"
        verbose_name_plural = "Courses"
