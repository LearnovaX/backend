from rest_framework import serializers

from src.apps.users.models import User, UserProfile


class ImportUserSerializer(serializers.ModelSerializer):
    profile = serializers.DictField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "email_verified",
            "must_set_password",
            "profile",
        ]

    def create(self, validated_data):
        profile_data = validated_data.pop("profile", {})
        user = User.objects.create(**validated_data)
        # The signal already creates a UserProfile, so just update it if needed
        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile_data:
            for field, value in profile_data.items():
                setattr(profile, field, value)
            profile.save()
        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", {})
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if profile_data:
            UserProfile.objects.update_or_create(user=instance, defaults=profile_data)
        return instance
