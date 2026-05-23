from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from src.apps.common.models import BaseModel
from src.apps.submissions.models import Answer
from src.apps.users.models import User


class Grade(BaseModel):
    answer = models.OneToOneField(Answer, on_delete=models.CASCADE, related_name="grade")
    score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    feedback_text = models.TextField(null=True, blank=True)
    max_score = models.IntegerField(default=100.00, validators=[MinValueValidator(0)])
    graded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="graded_answers")

    def __str__(self):
        return (
            f"{self.answer.user.first_name} - {self.score}/{self.max_score} for "
            f"{self.answer.task.name}"
        )

    @property
    def percentage(self):
        if self.score and self.max_score:
            return (self.score / self.max_score) * 100 if self.max_score > 0 else 0
        return 0

    @property
    def letter_grade(self):
        percentage = self.percentage
        if percentage >= 90:
            return "A"
        elif percentage >= 70:
            return "B"
        elif percentage >= 50:
            return "C"
        elif percentage >= 31:
            return "D"
        else:
            return "F"

    class Meta:
        db_table = "Grades"
        verbose_name = "Grade"
        verbose_name_plural = "Grades"
