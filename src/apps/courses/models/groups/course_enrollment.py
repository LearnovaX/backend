from django.db import models
from django.db.models import Q

from src.apps.courses.models import Course
from src.apps.courses.models.groups.course_groups import CourseGroup
from src.apps.users.models import User


class CourseEnrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    group = models.ForeignKey(CourseGroup, on_delete=models.CASCADE, related_name="members")
    role = models.CharField(
        max_length=20,
        choices=[("student", "Student"), ("assistant", "Assistant"), ("teacher", "Teacher")],
        default="student",
    )
    enrolled_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Enrollment for '{self.course.name}, {self.course.description[:20]}...'"
            f" for {self.user.first_name} in "
            f"'{self.group.name} group'"
        )

    class Meta:
        db_table = "Course Enrollments"
        verbose_name = "Course Enrollment"
        verbose_name_plural = "Course Enrollments"
        # Replace old unique_together with conditional constraints:
        constraints = [
            # Students can be in only one group per course
            models.UniqueConstraint(
                fields=["user", "course"],
                condition=Q(role="student"),
                name="uniq_student_per_course",
            ),
            # No duplicate (user, group, role)
            models.UniqueConstraint(
                fields=["user", "group", "role"],
                name="uniq_user_group_role",
            ),
        ]
