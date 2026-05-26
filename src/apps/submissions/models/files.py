from django.db import models

from src.apps.common.models import BaseModel
from src.apps.common.utils import unique_file_path

from .answers import Answer


class AnswerFile(BaseModel):
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to=unique_file_path, null=True, blank=True)

    original_name = models.CharField(max_length=255, null=True, blank=True)
    size = models.PositiveIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.file:
            self.original_name = self.file.name.split("/")[-1]
            self.size = self.file.size
            self.content_type = getattr(self.file.file, "content_type", None)
        super().save(*args, **kwargs)
