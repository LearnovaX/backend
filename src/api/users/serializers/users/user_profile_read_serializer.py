from rest_framework import serializers

from src.apps.users.models import UserProfile

from .user_serializer import UserSerializer


class UserProfileReadSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "user",
            "middle_name",
            "interface_language",
            "timezone",
            "birth_date",
            "profile_edit_blocked",
            "deactivation_time",
            "days_to_delete_after_deactivation",
            "phone_number",
            "company",
            "profile_photo",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        user = getattr(request, "user", None)

        is_admin = bool(
            user and user.is_authenticated and user.groups.filter(name="Admins").exists()
        )
        if not is_admin:
            for f in ("deactivation_time", "days_to_delete_after_deactivation"):
                self.fields.pop(f, None)

        instance = self.instance if isinstance(self.instance, UserProfile) else None
        is_student = bool(
            user and user.is_authenticated and user.groups.filter(name="Students").exists()
        )
        if is_student and instance and instance.profile_edit_blocked:
            for name in ("birth_date", "profile_photo", "phone_number", "company"):
                if name in self.fields:
                    self.fields[name].read_only = True

            user_field = self.fields.get("user")
            if user_field and hasattr(user_field, "fields"):
                for name in ("first_name", "last_name", "email"):
                    if name in user_field.fields:
                        user_field.fields[name].read_only = True
