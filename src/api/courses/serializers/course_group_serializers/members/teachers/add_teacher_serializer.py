from django.db import transaction
from rest_framework import serializers

from src.apps.courses.models import CourseEnrollment, CourseGroup
from src.apps.users.models import User


class AddTeachersSerializer(serializers.Serializer):
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
        created = []
        errors = []
        with transaction.atomic():
            for uid in self.validated_data["user_ids"]:
                try:
                    u = User.objects.get(pk=uid)
                except User.DoesNotExist:
                    errors.append({"user_id": uid, "error": "not found"})
                    continue
                # one teacher enrollment per group
                obj, _ = CourseEnrollment.objects.update_or_create(
                    user=u,
                    group=group,
                    role="teacher",
                    defaults={"course": group.course},
                )
                created.append(obj.id)
        qs = CourseEnrollment.objects.filter(id__in=created).select_related("user")
        return {"created": qs, "errors": errors}
