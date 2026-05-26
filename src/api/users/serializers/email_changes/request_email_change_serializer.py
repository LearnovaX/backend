from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from src.apps.common.utils import generate_random_code
from src.apps.users.models import EmailVerification, User
from src.apps.users.service import send_email_to_verify_email


class RequestEmailChangeSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=255)
    new_email = serializers.EmailField()

    # TODO -> IntegrityError occurred, check and test
    def validate(self, attrs):
        user_id = attrs.get("user_id")
        new_email = attrs.get("new_email")

        user = User.objects.filter(pk=user_id).first()
        if not user:
            raise ValidationError(f"User with {user_id} id not found")
        if not new_email:
            raise ValidationError("New email didn't provided.")
        if User.objects.filter(email=new_email).exists():
            raise ValidationError(f"User with {new_email} email already exists.")

        code = generate_random_code()
        send_email_to_verify_email(new_email, user.first_name, code)

        with transaction.atomic():
            EmailVerification.objects.filter(user=user).delete()
            EmailVerification.objects.filter(new_email=new_email).delete()
            EmailVerification.objects.update_or_create(user=user, new_email=new_email, code=code)

        return attrs
