from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from src.apps.users.models import UserProfile


class UserProfileWriteSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False)
    middle_name = serializers.CharField(source="user.middle_name", required=False)
    mfa_enabled = serializers.BooleanField(source="user.mfa_enabled", required=False, default=False)

    class Meta:
        model = UserProfile
        fields = [
            "first_name",
            "last_name",
            "middle_name",
            "mfa_enabled",
            "interface_language",
            "timezone",
            "birth_date",
            "phone_number",
            "company",
            "profile_photo",
            "profile_edit_blocked",
            "deactivation_time",
            "days_to_delete_after_deactivation",
            "updated_at",
        ]
        read_only_fields = ("updated_at", "deactivation_time", "days_to_delete_after_deactivation")
        extra_kwargs = {
            "timezone": {"required": False},
            "interface_language": {"required": False},
            "company": {"required": False},
            "birth_date": {"required": False},
            "middle_name": {"required": False},
            "profile_photo": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        req = self.context.get("request")
        user = getattr(req, "user", None)
        is_admin = bool(
            user and user.is_authenticated and user.groups.filter(name="Admins").exists()
        )

        if not is_admin:
            for name in (
                "profile_edit_blocked",
                "deactivation_time",
                "days_to_delete_after_deactivation",
            ):
                if name in self.fields:
                    self.fields.pop(name, None)
                    # self.fields[name].read_only = True

    def validate(self, attrs):
        req = self.context.get("request")
        user = getattr(req, "user", None)
        is_admin = bool(
            user and user.is_authenticated and user.groups.filter(name="Admins").exists()
        )
        instance = self.instance

        if instance and instance.profile_edit_blocked and not is_admin:
            raise ValidationError("Profile editing is blocked by an administrator.")

        user_data = attrs.get("user", {})
        if "email" in user_data:
            raise ValidationError("Use the email change flow to update your email address.")

        return attrs

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if user_data:
            changed = False
            for attr in ("first_name", "last_name", "mfa_enabled"):
                if attr in user_data:
                    setattr(instance.user, attr, user_data[attr])
                    changed = True
            if changed:
                instance.user.save()

        return instance
