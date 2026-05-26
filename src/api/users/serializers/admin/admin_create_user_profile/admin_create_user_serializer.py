import logging

from django.contrib.auth.models import Group
from rest_framework import serializers

from src.apps.users.models import Role, User, UserProfile

from .admin_profile_nested_create_serializer import AdminProfileNestedCreateSerializer

logger = logging.getLogger(__name__)


class AdminCreateUserSerializer(serializers.ModelSerializer):
    profile = AdminProfileNestedCreateSerializer(required=False)
    role = serializers.ChoiceField(choices=Role.choices)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "profile"]

    def validate(self, attrs):
        email = attrs.get("email")
        if User.objects.filter(email=email).exists():
            logger.warning(f"Bad request in user creation, user already exists with email {email}")
            raise serializers.ValidationError("User already registered in the system")

        return attrs

    def create(self, validated_data):
        profile_data = validated_data.pop("profile", {})
        role = validated_data.pop("role", None)

        user = User.objects.create(
            **validated_data,
            is_active=True,
            email_verified=False,
            must_set_password=True,
        )
        user.set_unusable_password()

        # The signal already creates a UserProfile, so just update it if needed
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile_data:
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()

        if role:
            name = {
                "admin": "Admins",
                "teacher": "Teachers",
                "assistant": "Assistants",
                "manager": "Managers",
                "student": "Students",
            }.get(role, "Students")
            group, _ = Group.objects.get_or_create(name=name)
            user.groups.add(group)
            user.role = role
        user.save()
        return user
