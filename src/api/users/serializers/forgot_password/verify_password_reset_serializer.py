from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from src.apps.users.models import CodePassword, User


class VerifyPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=4)

    def validate(self, attrs):
        email = attrs.get("email")
        code = attrs.get("code")

        if not email:
            raise ValidationError("Email session not found. Please request password reset again.")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("User not found.")

        try:
            code_db = CodePassword.objects.get(user=user)
        except CodePassword.DoesNotExist:
            raise ValidationError("Invalid verification code. Please try again.")

        if code_db.expire_date < timezone.now():
            raise ValidationError("Your code has expired. Request a new one.")

        if str(code_db.code) != str(code):
            raise ValidationError("Incorrect code. Please enter the correct code.")

        return attrs
