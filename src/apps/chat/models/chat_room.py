from django.core.exceptions import ValidationError
from django.db import models

from src.apps.common.models import BaseModel
from src.apps.courses.models import Course, CourseEnrollment
from src.apps.users.models import User


class ChatRoom(BaseModel):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="teacher_chat_rooms")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="student_chat_rooms")
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, null=True, blank=True, related_name="chat_rooms"
    )
    is_active = models.BooleanField(default=True)

    def clean(self):
        if self.teacher_id and self.student_id:
            # Check if they share any course where one is teacher and other is student
            shared_courses = CourseEnrollment.objects.filter(
                user=self.teacher,
                role="teacher",
                course__enrollments__user=self.student,
                course__enrollments__role="student",
            ).exists()

            if not shared_courses:
                raise ValidationError(
                    "Chat can only be created between teacher and their students in the same course"
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def room_name(self):
        """Generate unique room name for WebSocket groups"""
        return (
            f"chat_{min(self.student_id, self.teacher_id)}_"
            f"{max(self.student_id, self.teacher_id)}"
        )

    def get_other_user(self, current_user):
        """Get the other participant in the chat"""
        return self.student if current_user == self.teacher else self.teacher

    def __str__(self):
        return f"Chat: {self.teacher.first_name} <-> {self.student.first_name}"

    class Meta:
        db_table = "Chat_Rooms"
        verbose_name = "Chat Room"
        verbose_name_plural = "Chat Rooms"
        unique_together = ("teacher", "student")
        ordering = ("-updated_at",)
