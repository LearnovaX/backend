from rest_framework import serializers

from src.apps.users.models import User


class ExportUserSerializer(serializers.ModelSerializer):
    middle_name = serializers.SerializerMethodField()
    interface_language = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()
    birth_date = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_superuser",
            "email_verified",
            "must_set_password",
            "date_joined",
            "last_login",
            "middle_name",
            "interface_language",
            "timezone",
            "birth_date",
            "phone_number",
            "company",
        ]

    def get_middle_name(self, obj: User) -> str | None:
        if hasattr(obj, "profile"):
            return obj.profile.middle_name
        return None

    def get_interface_language(self, obj: User) -> str | None:
        if hasattr(obj, "profile"):
            return obj.profile.interface_language
        return None

    def get_timezone(self, obj: User) -> str | None:
        if hasattr(obj, "profile"):
            return obj.profile.timezone
        return None

    def get_birth_date(self, obj: User):
        if hasattr(obj, "profile"):
            return obj.profile.birth_date
        return None

    def get_phone_number(self, obj: User) -> str | None:
        if hasattr(obj, "profile"):
            return obj.profile.phone_number
        return None

    def get_company(self, obj: User) -> str | None:
        if hasattr(obj, "profile"):
            return obj.profile.company
        return None
