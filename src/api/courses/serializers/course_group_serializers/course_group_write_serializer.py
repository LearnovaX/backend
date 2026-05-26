from rest_framework import serializers

from src.apps.courses.models import CourseGroup


class CourseGroupWriteSerializer(serializers.ModelSerializer):
    registration_link = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseGroup
        fields = [
            "name",
            "course",
            "students_limit",
            "self_registration",
            "is_active",
            "registration_link",
            "token_validity_hours",
            "token_validity_days",
        ]
        extra_kwargs = {"is_active": {"required": False}}

    # def __init__(self, *args, **kwargs):
    # super().__init__(*args, **kwargs)
    # group, _ = Group.objects.get_or_create(name="Teachers")
    # self.fields["teacher"].queryset = User.objects.filter(groups__name="Teachers")

    def validate(self, attrs):
        """Validate that at least one of hours or days is provided when self_registration is True"""
        self_registration = attrs.get("self_registration", False)
        token_validity_hours = attrs.get("token_validity_hours")
        token_validity_days = attrs.get("token_validity_days")

        if self_registration:
            # Allow both None values (no expiration) or at least one valid value
            if token_validity_hours is not None and token_validity_hours < 0:
                raise serializers.ValidationError(
                    {"token_validity_hours": "Must be greater than 0 if specified."}
                )
            if token_validity_days is not None and token_validity_days < 0:
                raise serializers.ValidationError(
                    {"token_validity_days": "Must be greater than 0 if specified."}
                )

        return attrs

    def get_registration_link(self, obj: CourseGroup):
        request = self.context.get("request")
        if not request:
            return None
        user = request.user
        if user.groups.filter(name="Admins").exists():
            if obj.self_registration and obj.is_token_expired():
                return "Registration link is expired"
            return obj.registration_link
        return None
