from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from src.apps.users.models import CodeEmail


class VerifyRegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs.get("email")
        code = attrs.get("code")

        if not code:
            raise ValidationError("Verification code is required")

        code_db = CodeEmail.objects.filter(email=email).first()
        if not code_db:
            raise ValidationError("Verification code not found. Please request a new code.")

        if code_db.expire_date < timezone.now():
            raise ValidationError("Verification code has expired. Please request a new code.")

        if str(code_db.code) != str(code):
            raise ValidationError("Invalid verification code.")

        code_db.delete()

        return attrs
