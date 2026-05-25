from rest_framework import serializers

from src.apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    # role = serializers.SerializerMethodField(read_only=True)
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    status = serializers.SerializerMethodField()
    profile_photo = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "mfa_enabled",
            "date_joined",
            "last_login",
            "role",
            "profile_photo",
            "groups",
            "status",
        ]
        extra_kwargs = {"role": {"required": False}}

    def get_fields(self):
        fields = super().get_fields()
        include = self.context.get("include_profile_photo", False)
        if not include:
            fields.pop("profile_photo", None)
        return fields

    def get_groups(self, obj: User):
        return obj.groups.values_list("name", flat=True)

    def get_status(self, obj: User) -> str:
        if obj.is_active and not obj.must_set_password and obj.email_verified:
            return "Authorized"
        elif obj.is_active and (obj.must_set_password or not obj.email_verified):
            return "Unauthorized"
        profile = obj.profile
        if not obj.is_active and profile.days_to_delete_after_deactivation:
            return "Awaiting deletion"
        return "Deactivated"

    def get_profile_photo(self, obj: User):
        if hasattr(obj, "profile") and obj.profile and obj.profile.profile_photo:
            return obj.profile.profile_photo.url
        return None

    # def get_role(self, obj):
    #     groups = obj.groups.all()
    #     if groups.exists():
    #         return groups.first().name
    #     return None
