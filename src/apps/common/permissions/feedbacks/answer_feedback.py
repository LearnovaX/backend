from rest_framework.permissions import BasePermission

from src.apps.courses.models import CourseEnrollment, CourseGroup


class CanAccessAnswerFeedback(BasePermission):
    """
    Students can only see feedback on their own answers.
    Teachers can see feedback on answers from their course group students.
    Admins can see all feedback.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        user_groups = [group.name for group in user.groups.all()]

        # Get the answer (obj could be Answer or AnswerFeedback)
        if hasattr(obj, "answer"):  # AnswerFeedback object
            answer = obj.answer
        else:  # Answer object
            answer = obj

        # Students can only access their own answer's feedback
        if "Students" in user_groups:
            return answer.user == user

        # Admins can access all feedback
        if "Admins" in user_groups:
            return True

        # Teachers can access feedback for answers from their course group students
        if "Teachers" in user_groups:
            teacher_groups = CourseGroup.objects.filter(teacher=user)
            student_enrollment = CourseEnrollment.objects.filter(
                user=answer.user,
                course=answer.task.course,
                group__in=teacher_groups,
                role="student",
            ).exists()
            return student_enrollment

        return False
