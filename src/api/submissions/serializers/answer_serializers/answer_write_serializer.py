from django.utils import timezone
from rest_framework import serializers

from src.apps.assignments.models import Task
from src.apps.submissions.models import Answer, AnswerFile


class AnswerWriteSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_null=True,
        max_length=30,
    )

    class Meta:
        model = Answer
        fields = ["id", "task", "description", "files", "status"]
        extra_kwargs = {
            "files": {"required": False},
            "id": {"read_only": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if request and request.user:
            user_groups = request.user.cached_group_names

            # Students can only create answers for themselves
            if "Students" in user_groups:
                # Remove user field from students - will be set automatically
                if "user" in self.fields:
                    del self.fields["user"]
                # Students can't set status
                self.fields["status"].read_only = True

            # Teachers/Admins can't modify content, only status (when updating)
            elif any(group in user_groups for group in ["Teachers", "Admins"]):
                if self.instance:  # This is an update
                    self.fields["description"].read_only = True
                    self.fields["files"].read_only = True
                    self.fields["task"].read_only = True
                    if "user" in self.fields:
                        del self.fields["user"]  # Can't change answer owner

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")

        if request and request.user:
            user_groups = request.user.cached_group_names

            # Students can only modify their own answers and can't set status
            if "Students" in user_groups:
                fields["status"].read_only = True

        return fields

    def validate_files(self, files):
        if len(files) > 30:
            raise serializers.ValidationError("Maximum 30 number of files exceeded")

        max_file_size = 10 * 1024 * 1024
        for file in files:
            if file.size > max_file_size:
                raise serializers.ValidationError("File size exceeded")

        return files

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        user_groups = user.cached_group_names

        # Students: force user and default status on create
        if user and "Students" in user_groups:
            attrs["user"] = user
            attrs["status"] = Answer.Status.in_review

        # Resolve task: prefer incoming value, fallback to instance
        task_val = attrs.get("task", None)

        if task_val is None and self.instance:
            # Use the existing instance's task for updates where client didn't resend task
            task = getattr(self.instance, "task", None)
        else:
            # task_val might be a Task instance or a PK
            if isinstance(task_val, Task):
                task = task_val
            else:
                try:
                    task = Task.objects.get(pk=task_val)
                except (TypeError, ValueError, Task.DoesNotExist):
                    raise serializers.ValidationError({"task": "Task not found or invalid."})

        if not task:
            raise serializers.ValidationError({"task": "Task is required."})

        # If this is an update performed by a teacher/admin that only changes status,
        # allow it without enforcing previous-task sequencing/deadline rules.
        if self.instance and any(g in user_groups for g in ["Teachers", "Admins"]):
            # If incoming attrs are only about status (and maybe files not present here),
            # skip owner/course sequencing checks.
            incoming_only_status = set(attrs.keys()) <= {"status"}
            if incoming_only_status:
                return attrs

        # Now run course-related validations based on resolved task
        course = task.course

        # Sequence enforcement for non-free-order courses
        if not course.free_order:
            current_task_number = task.number
            previous_task = course.tasks.filter(number=current_task_number - 1).first()
            if previous_task:
                previous_answer = None
                if user:
                    previous_answer = Answer.objects.filter(user=user, task=previous_task).first()

                if not previous_answer or previous_answer.status != Answer.Status.approved:
                    raise serializers.ValidationError(
                        "You are not allowed to submit this task. "
                        "Please submit the previous task first."
                    )

        # Deadline check
        if course.deadline_to_finish_course and course.deadline_to_finish_course < timezone.now():
            raise serializers.ValidationError(
                "Deadline for finishing tasks in this course is overdue"
            )

        return attrs

    def create(self, validated_data):
        files_data = validated_data.pop("files", None)
        answer = Answer.objects.create(**validated_data)

        if files_data:
            for file_data in files_data:
                AnswerFile.objects.create(answer=answer, file=file_data)

        return answer

    def update(self, instance, validated_data):
        files_data = validated_data.pop("files", None)
        request = self.context.get("request")

        if request:
            user_groups = request.user.cached_group_names

            # Students can't modify status
            if "Students" in user_groups:
                validated_data["status"] = Answer.Status.in_review

            # Teachers and Admins can ONLY modify status
            elif any(group in user_groups for group in ["Teachers", "Admins"]):
                # Remove all fields except status
                allowed_fields = {"status"}
                validated_data = {k: v for k, v in validated_data.items() if k in allowed_fields}

        # Update allowed fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Handle files only for students
        if files_data is not None and request:
            user_groups = request.user.cached_group_names
            if "Students" in user_groups:
                # Replace all existing files
                instance.files.all().delete()
                for file_data in files_data:
                    AnswerFile.objects.create(answer=instance, file=file_data)

        if request and "Students" in request.user.cached_group_names:
            instance.plagiarism_status = Answer.PlagiarismStatus.pending_analysis
            instance.extracted_text = ""
            instance.analyzed_at = None

        instance.save()
        return instance
