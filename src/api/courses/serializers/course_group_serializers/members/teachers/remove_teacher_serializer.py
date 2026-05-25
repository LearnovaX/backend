from django.db import transaction
from rest_framework import serializers

from src.apps.courses.models import CourseEnrollment, CourseGroup


class RemoveTeachersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)

    def validate(self, data):
        request = self.context.get("request")
        group: CourseGroup = self.context.get("group")
        if not request or not group:
            raise serializers.ValidationError("Request and group required in context")
        if not request.user.groups.filter(name="Admins").exists():
            raise serializers.ValidationError("Permission denied")
        data["user_ids"] = list(dict.fromkeys(data["user_ids"]))
        return data

    def save(self):
        group: CourseGroup = self.context["group"]
        removed, errors = [], []
        with transaction.atomic():
            for uid in self.validated_data["user_ids"]:
                qs = CourseEnrollment.objects.filter(user_id=uid, group=group, role="teacher")
                if qs.exists():
                    qs.delete()
                    removed.append(uid)
                else:
                    errors.append({"user_id": uid, "error": "enrollment not found"})
        return {"removed": removed, "errors": errors}
