from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from src.apps.users.models import EmailVerification, User


class ConfirmEmailChangeSerializer(serializers.Serializer):
    new_email = serializers.EmailField()
    code = serializers.CharField(max_length=10)

    def validate(self, attrs):
        new_email = attrs.get("new_email")
        code = attrs.get("code")

        code_db = EmailVerification.objects.filter(new_email=new_email).first()
        user = User.objects.filter(pk=code_db.user.pk).first()

        if not code or not new_email:
            raise ValidationError("new_email or code didn't provided")

        if not user:
            raise ValidationError("User not found in database")

        if code_db.expire_date < timezone.now():
            raise ValidationError("Your code has expired. Request a new one.")

        if str(code_db.code) != str(code):
            raise ValidationError("Incorrect code. Please enter the correct code.")

        user.email = new_email
        user.save()

        return attrs
