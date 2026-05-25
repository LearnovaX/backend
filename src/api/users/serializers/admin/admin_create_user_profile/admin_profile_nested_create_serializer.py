from rest_framework import serializers

from src.apps.users.models import UserProfile


class AdminProfileNestedCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "middle_name",
            "interface_language",
            "timezone",
            "birth_date",
            "phone_number",
            "company",
            "profile_photo",
            "deactivation_time",
            "days_to_delete_after_deactivation",
            "profile_edit_blocked",
        ]
        extra_kwargs = {
            "timezone": {"required": False},
            "interface_language": {"required": False},
            "company": {"required": False},
            "birth_date": {"required": False},
            "middle_name": {"required": False},
            "profile_photo": {"required": False},
        }
