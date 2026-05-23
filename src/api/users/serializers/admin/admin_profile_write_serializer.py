import logging

from rest_framework import serializers

from src.apps.users.models import UserProfile

logger = logging.getLogger(__name__)


class AdminProfileWriteSerializer(serializers.ModelSerializer):
    profile_photo = serializers.ImageField(required=False, allow_null=True)

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
            "profile_edit_blocked",
            "deactivation_time",
            "days_to_delete_after_deactivation",
            "updated_at",
        ]
        read_only_fields = ("updated_at",)
        extra_kwargs = {
            "timezone": {"required": False},
            "interface_language": {"required": False},
            "company": {"required": False},
            "birth_date": {"required": False},
            "middle_name": {"required": False},
            "profile_photo": {"required": False},
            "days_to_delete_after_deactivation": {"required": False},
            "phone_number": {"validators": []},
        }

    def validate_phone_number(self, value):
        if value is None or value == "":
            return value

        queryset = UserProfile.objects.filter(phone_number=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            logger.warning(f"users.PROFILE_UPDATE BAD REQUEST. Phone number {value} already exists")
            raise serializers.ValidationError("User Profile with this phone number already exists.")

        return value

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
