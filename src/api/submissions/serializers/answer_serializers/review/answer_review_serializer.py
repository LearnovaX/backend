from django.db import transaction
from rest_framework import serializers

from src.apps.common.utils import (
    send_realtime_status_notification,
    send_status_change_email_helper,
)
from src.apps.grades.models import Grade
from src.apps.notifications.models import Notification
from src.apps.submissions.models import Answer


class AnswerReviewSerializer(serializers.ModelSerializer):
    """
    Combined serializer for updating answer status and providing feedback.
    Fixes:
      - Ensures current_* vars are always initialized to avoid UnboundLocalError.
      - Ensures a safe notification title/content exist on every path.
      - Avoids showing 'None' in grade lines.
    """

    feedback_text = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True,
        help_text="Optional feedback text for the student",
    )
    score = serializers.IntegerField(required=False, allow_null=True)
    max_score = serializers.IntegerField(required=False, allow_null=True)
    delete_grade = serializers.BooleanField(required=False, default=False)

    class Meta:
        model = Answer
        fields = ["status", "feedback_text", "score", "max_score", "delete_grade"]

    def validate_status(self, value):
        if value not in dict(Answer.Status.choices):
            raise serializers.ValidationError("Invalid status value")
        return value

    def validate_feedback_text(self, value):
        if value and not value.strip():
            raise serializers.ValidationError("Feedback text cannot be empty if provided")
        return value.strip() if value else value

    def update(self, instance, validated_data):
        with transaction.atomic():
            # Lock the row for a consistent update
            instance = Answer.objects.select_for_update().get(pk=instance.pk)

            previous_status = instance.status
            new_status = validated_data.get("status", instance.status)
            status_changed = previous_status != new_status

            # Pop grade-related fields early so we don't accidentally setattr() them
            score = validated_data.pop("score", None)
            max_score = validated_data.pop("max_score", None)
            feedback_text = validated_data.pop("feedback_text", None)
            delete_grade = validated_data.pop("delete_grade", False)

            # Update answer fields (e.g., status)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Grade handling
            grade_changed = False
            is_deleted = False
            grade_action = ""
            existing_grade = getattr(instance, "grade", None)
            had_grade = existing_grade is not None

            # Old values (for change detection)
            old_score = existing_grade.score if had_grade else None
            old_max_score = existing_grade.max_score if had_grade else None
            old_feedback = existing_grade.feedback_text if had_grade else None

            # Initialize "current" values so they're ALWAYS defined (prevents UnboundLocalError)
            current_feedback = old_feedback or ""
            current_score = old_score
            current_max_score = old_max_score
            current_percentage = existing_grade.percentage if had_grade else None
            current_letter = existing_grade.letter_grade if had_grade else None

            if delete_grade:
                if existing_grade:
                    existing_grade.delete()
                    grade_changed = True
                    is_deleted = True
                    grade_action = "removed"
                    current_feedback = ""
                    current_score = None
                    current_max_score = None
                    current_percentage = None
                    current_letter = None
            else:
                # Only touch grade if something was provided
                if any([score is not None, max_score is not None, feedback_text is not None]):
                    if not existing_grade:
                        existing_grade = Grade(
                            answer=instance,
                            graded_by=self.context["request"].user,
                        )
                        grade_action = "added"

                    if new_status == Answer.Status.approved:
                        if score is not None:
                            existing_grade.score = score
                        if max_score is not None:
                            # keep original behavior (fallback to 100 if falsy)
                            existing_grade.max_score = max_score or 100
                    else:
                        # For non-approved statuses, clear score as per original intent
                        existing_grade.score = None

                    if feedback_text is not None:
                        existing_grade.feedback_text = feedback_text

                    existing_grade.save()

                    # Detect actual change
                    if (
                        existing_grade.score != old_score
                        or existing_grade.max_score != old_max_score
                        or existing_grade.feedback_text != old_feedback
                    ):
                        grade_changed = True

                    if not had_grade:
                        grade_changed = True
                        grade_action = "added"
                    elif grade_action == "":
                        grade_action = "updated"

                    # Refresh current_* from saved grade
                    current_feedback = existing_grade.feedback_text or ""
                    current_score = existing_grade.score
                    current_max_score = existing_grade.max_score
                    current_percentage = existing_grade.percentage
                    current_letter = existing_grade.letter_grade

            # Build & send notifications
            if status_changed or grade_changed:
                # Human-friendly messages for known statuses
                status_messages = {
                    "approved": "Great job! Your answer has been approved ✅.",
                    "rejected": "Unfortunately, your answer was rejected ❌."
                    " Please review the task requirements and try again.",
                    # noqa E402
                    "have_flaws": "Your answer has some issues ⚠️. "
                    "Please check the feedback and make the necessary improvements.",
                    # noqa E402
                }

                task_title = f"Task {instance.task.number}. {instance.task.name}"
                current_status_display = dict(Answer.Status.choices)[instance.status]

                title = None
                content = ""

                if status_changed and instance.status in status_messages:
                    status_action = (
                        "reviewed" if previous_status == Answer.Status.in_review else "updated"
                    )
                    title = f"Your answer for {task_title} has been {status_action}"
                    content = (
                        f"{status_messages[instance.status]}\n\n"
                        f"Task: {instance.task.name} (#{instance.task.number})\n"
                        f"Status: {current_status_display}"
                    )

                # Helper to render grade line nicely (avoid None-values)
                def build_grade_lines(_score, _max, _perc, _letter, _feedback):
                    lines = []
                    if (
                        _score is not None
                        and _max is not None
                        and _perc is not None
                        and _letter is not None
                    ):
                        lines.append(f"Grade: {_score}/{_max} ({_perc}% - {_letter})")
                    if (_feedback or "").strip():
                        lines.append(f"Feedback: {_feedback.strip()}")
                    return "\n".join(lines)

                if grade_changed:
                    grade_lines = ""
                    if not is_deleted:
                        grade_lines = build_grade_lines(
                            current_score,
                            current_max_score,
                            current_percentage,
                            current_letter,
                            current_feedback,
                        )

                    if status_changed:
                        # Extend the existing title/content
                        grade_suffix = f" with grade {grade_action}"
                        title = (
                            title or f"Your answer for {task_title} has been updated"
                        ) + grade_suffix
                        if is_deleted:
                            content += "\n\nThe grade has been removed."
                        elif grade_lines:
                            content += f"\n\n{grade_lines}"
                    else:
                        # No status change, only grade change
                        title = f"Your grade for {task_title} has been {grade_action}"
                        if is_deleted:
                            content = (
                                f"The grade for your answer has been removed."
                                f"\n\nStatus: {current_status_display}"
                            )
                        else:
                            # Include grade lines + status
                            if grade_lines:
                                content = f"{grade_lines}\n\nStatus: {current_status_display}"
                            else:
                                content = f"Status: {current_status_display}"

                # If we still don't have a title (e.g., unrecognized status but status changed),
                if not title:
                    if status_changed and not grade_changed:
                        title = f"Your answer for {task_title} has been updated"
                        if not content:
                            content = f"Status: {current_status_display}"
                    elif not (status_changed or grade_changed):
                        # Shouldn't happen due to outer guard, but keep safe
                        return instance

                # Create/update notification safely (feedback always defined)
                notification, _ = Notification.objects.update_or_create(
                    receiver=instance.user,
                    title=title,
                    defaults={
                        "content": content,
                        "feedback": current_feedback if not is_deleted else "",
                        # "sender": self.context.get("request").user,
                    },
                )

                send_realtime_status_notification(notification=notification)
                send_status_change_email_helper(notification_instance=notification)

            return instance
