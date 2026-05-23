from rest_framework import serializers

from src.apps.users.models import User, UserProfile


class AdminProfileReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
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


class AdminUserReadSerializer(serializers.ModelSerializer):
    profile = AdminProfileReadSerializer(read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
            "last_login",
            "profile",
            "status",
        ]

    def get_status(self, obj: User) -> str:
        if obj.is_active and not obj.must_set_password and obj.email_verified:
            return "Authorized"
        elif obj.is_active and (obj.must_set_password or not obj.email_verified):
            return "Unauthorized"
        profile = obj.profile
        if not obj.is_active and profile.days_to_delete_after_deactivation:
            return "Awaiting deletion"
        return "Deactivated"
