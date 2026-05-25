from django.contrib.auth.models import Group
from rest_framework import serializers

from src.apps.users.models import Role, User, UserProfile

from .admin_profile_write_serializer import AdminProfileWriteSerializer


class AdminUpdateUserSerializer(serializers.ModelSerializer):
    profile = AdminProfileWriteSerializer(required=False)
    role = serializers.ChoiceField(choices=Role.choices, required=False)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "profile"]
        extra_kwargs = {"email": {"required": False}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, "profile") and self.instance.profile:
            self.fields["profile"].instance = self.instance.profile

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        role = validated_data.pop("role", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data is not None:
            profile = instance.profile
            if profile is None:
                profile = UserProfile.objects.create(user=instance)

            # Now we can update directly since validation already passed
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()

        if role:
            name = {
                "admin": "Admins",
                "teacher": "Teachers",
                "assistant": "Assistants",
                "manager": "Managers",
                "student": "Students",
            }.get(role, "Students")
            instance.groups.clear()
            group, _ = Group.objects.get_or_create(name=name)
            instance.groups.add(group)
            instance.role = role
            instance.save()

        return instance
