from django.contrib.auth.models import Group
from rest_framework import serializers

from src.apps.users.models import User


class RegisterSerializer(serializers.ModelSerializer):
    re_password = serializers.CharField(write_only=True, max_length=255)
    password = serializers.CharField(write_only=True, max_length=255)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password", "re_password"]

    def validate(self, attrs):
        re_password = attrs.get("re_password", None)
        password = attrs.get("password", None)
        if not re_password or not password:
            raise serializers.ValidationError("Please provide password")

        if str(attrs["password"]) != str(attrs["re_password"]):
            raise serializers.ValidationError("Passwords don't match")

        email = attrs.get("email", None)

        if not email:
            raise serializers.ValidationError("No email provided.")

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User already registered in the system")

        return attrs

    def create(self, validated_data):
        validated_data.pop("re_password")
        password = validated_data.pop("password")

        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.role = "student"
        user.email_verified = True
        user.must_set_password = False
        user.is_active = False
        user_group, _ = Group.objects.get_or_create(name="Students")
        user.groups.add(user_group)
        user.save()

        return user
