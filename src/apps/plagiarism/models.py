from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings
from django.db import models
from django.utils import timezone

from src.apps.common.models import BaseModel
from src.apps.submissions.models import Answer


class PlagiarismReport(BaseModel):
    class ReviewStatus(models.TextChoices):
        pending_review = "pending_review", "Pending review"
        false_positive = "false_positive", "False positive"
        confirmed_suspicious = "confirmed_suspicious", "Confirmed suspicious"

    submission_a = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="plagiarism_reports_as_a",
    )
    submission_b = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name="plagiarism_reports_as_b",
    )
    similarity_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    flagged = models.BooleanField(default=False)
    review_status = models.CharField(
        max_length=32,
        choices=ReviewStatus.choices,
        default=ReviewStatus.pending_review,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_plagiarism_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        if self.submission_a_id and self.submission_b_id:
            first_id, second_id = sorted((self.submission_a_id, self.submission_b_id))
            self.submission_a_id = first_id
            self.submission_b_id = second_id
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Answer {self.submission_a_id} vs {self.submission_b_id}: "
            f"{self.similarity_score:.2%}"
        )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(submission_a=models.F("submission_b")),
                name="plagiarism_report_no_self_compare",
            ),
            models.UniqueConstraint(
                fields=["submission_a", "submission_b"],
                name="unique_plagiarism_report_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["submission_a", "submission_b"]),
            models.Index(fields=["flagged", "created_at"]),
            models.Index(fields=["review_status", "created_at"]),
        ]

    def mark_reviewed(self, *, status: str, reviewer, note: str = "") -> None:
        self.review_status = status
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "review_note"])
