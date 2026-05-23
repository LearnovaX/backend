from django.db import transaction
from rest_framework import serializers

from src.apps.courses.models import CourseEnrollment


class RemoveStudentsSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )

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

        # dedupe
        data["user_ids"] = list(dict.fromkeys(data["user_ids"]))
        return data

    def save(self):
        group = self.context["group"]
        removed = []
        errors = []

        with transaction.atomic():
            for uid in self.validated_data["user_ids"]:
                try:
                    enrollment = CourseEnrollment.objects.get(user_id=uid, course=group.course)
                    enrollment.delete()
                    removed.append(uid)
                except CourseEnrollment.DoesNotExist:
                    errors.append({"user_id": uid, "error": "enrollment not found"})

        return {"removed": removed, "errors": errors}
