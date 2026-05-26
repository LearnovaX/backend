from django.db import models

from src.apps.assignments.models import Task
from src.apps.common.models import BaseModel
from src.apps.users.models import User


class Answer(BaseModel):
    class Status(models.TextChoices):
        in_review = "in_review", "In review"
        approved = "approved", "Approved"
        have_flaws = "have_flaws", "Have Flaws"
        rejected = "rejected", "Rejected"

    class PlagiarismStatus(models.TextChoices):
        pending_analysis = "pending_analysis", "Pending analysis"
        analyzed = "analyzed", "Analyzed"
        failed = "failed", "Failed"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="answers")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="answers")
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.in_review)
    plagiarism_status = models.CharField(
        max_length=32,
        choices=PlagiarismStatus.choices,
        default=PlagiarismStatus.pending_analysis,
    )
    extracted_text = models.TextField(blank=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.task.name} task did {self.user.first_name} -"
            f" {self.description[:50]}... with '{self.status}' status"
        )

    class Meta:
        unique_together = [("user", "task")]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["task", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["plagiarism_status", "created_at"]),
            models.Index(fields=["task", "plagiarism_status"]),
        ]
        db_table = "Answers"
        verbose_name = "Answer"
        verbose_name_plural = "Answers"
