from django.db import transaction
from rest_framework import serializers

from src.apps.courses.models import CourseEnrollment
from src.apps.users.models import User


class AddStudentsSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate(self, data):
        request = self.context.get("request")
        group = self.context.get("group")
        if request is None or group is None:
            raise serializers.ValidationError(
                "Request and group must be passed in serializer context"
            )

        user = request.user
        if not user.groups.filter(name="Admins").exists():
            raise serializers.ValidationError("Permission denied")

        limit = getattr(group, "limit", None) or getattr(group, "students_limit", None)
        if limit is not None:
            current_students = group.members.filter(role="student").count()
            if current_students + len(data["user_ids"]) > limit:
                raise serializers.ValidationError(
                    {"user_ids": f"Too many students, maximum limit is {limit}"}
                )

        # optionally dedupe user_ids
        data["user_ids"] = list(dict.fromkeys(data["user_ids"]))
        return data

    def save(self):
        """Creates/updates CourseEnrollment entries for provided user_ids.
        Returns: {"created": <QuerySet of CourseEnrollment>, "errors": [..]}
        """
        group = self.context["group"]
        created_ids = []
        errors = []

        with transaction.atomic():
            for uid in self.validated_data["user_ids"]:
                try:
                    u = User.objects.get(pk=uid)
                except User.DoesNotExist:
                    errors.append({"user_id": uid, "error": "not found"})
                    continue
                # TODO -> check update_or_create method from project managers,
                #  do we need to update enrolled, if user enrolled for than one group?
                enrollment, _ = CourseEnrollment.objects.update_or_create(
                    user=u,
                    course=group.course,
                    defaults={"group": group, "role": "student"},
                )
                created_ids.append(enrollment.id)

        enrollments = CourseEnrollment.objects.filter(id__in=created_ids).select_related("user")
        return {"created": enrollments, "errors": errors}
