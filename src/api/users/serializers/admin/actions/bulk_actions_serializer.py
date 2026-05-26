import logging

from django.db import transaction
from django.http import FileResponse, HttpResponse
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from src.api.users.serializers.admin.files.export_user_serializer import ExportUserSerializer
from src.apps.common.utils.files.export_users import export_users_to_csv, export_users_to_xlsx
from src.apps.users.models import User

logger = logging.getLogger(__name__)


class BulkActionsSerializer(serializers.Serializer):
    """Serializer for bulk user actions with validation and business logic"""

    ACTION_CHOICES = [
        ("activate", "Activate"),
        ("deactivate", "Deactivate"),
        ("unauthorize", "Unauthorize"),
        ("export_csv", "Export csv"),
        ("export_xlsx", "Export xlsx"),
    ]

    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=100,  # Prevent bulk operations on too many users at once
        help_text="List of user IDs to perform action on (max 100)",
    )

    action = serializers.ChoiceField(
        choices=ACTION_CHOICES, help_text="Action to perform on selected users"
    )

    def validate_user_ids(self, value):
        """Validate that all user IDs exist and are accessible"""
        unique_ids = list(dict.fromkeys(value))

        existing_users = User.objects.filter(id__in=unique_ids)
        existing_ids = set(existing_users.values_list("id", flat=True))
        missing_ids = set(unique_ids) - existing_ids

        if missing_ids:
            logger.warning("users.BULK_ACTIONS. Missing user IDs: %s", missing_ids)
            raise ValidationError(f"The following user IDs do not exist: {sorted(missing_ids)}")

        return unique_ids

    def validate(self, attrs):
        """Cross-field validation and business logic checks"""
        user_ids = attrs["user_ids"]
        action = attrs["action"]

        users = User.objects.filter(id__in=user_ids).select_related("profile")

        if action == "activate":
            already_active = users.filter(is_active=True)
            if already_active.exists():
                active_count = already_active.count()
                attrs["warning"] = f"{active_count} user(s) are already active"

        elif action == "deactivate":
            already_inactive = users.filter(is_active=False)
            if already_inactive.exists():
                inactive_count = already_inactive.count()
                attrs["warning"] = f"{inactive_count} user(s) are already inactive"

            # Prevent deactivating superusers
            superusers = users.filter(is_superuser=True)
            if superusers.exists():
                superuser_emails = list(superusers.values_list("email", flat=True))
                raise ValidationError(f"Cannot deactivate superusers: {superuser_emails}")

        elif action == "unauthorize":
            already_unauthorized = users.filter(must_set_password=True)
            if already_unauthorized.exists():
                unauth_count = already_unauthorized.count()
                attrs["warning"] = f"{unauth_count} user(s) are already unauthorized"

            # Prevent unauthorizing superusers
            superusers = users.filter(is_superuser=True)
            if superusers.exists():
                superuser_emails = list(superusers.values_list("email", flat=True))
                raise ValidationError(f"Cannot unauthorize superusers: {superuser_emails}")

        attrs["users_queryset"] = users
        return attrs

    @transaction.atomic
    def perform_bulk_action(self):
        """Execute the bulk action with proper transaction handling"""
        action = self.validated_data["action"]
        warning = self.validated_data.get("warning", "")
        users = self.validated_data["users_queryset"]
        result = []
        if action == "activate":
            result = self._activate_users(users)
        elif action == "deactivate":
            result = self._deactivate_users(users)
        elif action == "unauthorize":
            result = self._unauthorize_users(users)
        elif action == "export_xlsx":
            result = self._export_to_excel(users)
        elif action == "export_csv":
            result = self._export_to_csv(users)

        if isinstance(result, (HttpResponse, FileResponse)):
            if warning:
                result["X-Bulk-Warning"] = warning
            return result

        if warning and isinstance(result, dict):
            logger.warning(f"users.BULK_ACTIONS. warning: {warning} with action: {action}")
            result["warning"] = warning

        return result

    @staticmethod
    def _activate_users(users):
        """Activate users and clear deactivation time"""
        inactive_users = users.filter(is_active=False)
        count = inactive_users.update(is_active=True)

        for user in inactive_users:
            user.is_active = True
            user.save()
        logger.info(f"users.BULK_ACTIONS. Activated {count} users")
        return {
            "message": f"Successfully activated {count} user(s)",
            "affected_count": count,
            "action_performed": "activate",
        }

    @staticmethod
    def _deactivate_users(users):
        """Deactivate users and set deactivation time"""
        active_users = users.filter(is_superuser=False)
        count = active_users.count()

        for user in active_users:
            user.is_active = False
            user.save()
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)

        logger.info(f"users.BULK_ACTIONS. Deactivated {count} users")
        return {
            "message": f"Successfully deactivated {count} user(s)",
            "affected_count": count,
            "action_performed": "deactivate",
        }

    @staticmethod
    def _unauthorize_users(users):
        """Unauthorize users (require password reset)"""
        # Only update users that are not already unauthorized (and not superusers)
        users = users.filter(is_superuser=False)
        i = 0
        for user in users:
            user.must_set_password = True
            user.set_unusable_password()
            for token in OutstandingToken.objects.filter(user=user):
                BlacklistedToken.objects.get_or_create(token=token)
            user.save()
            i += 1

        logger.info(f"users.BULK_ACTIONS. Unauthorized {i} users")
        return {
            "message": f"Successfully unauthorized {i} user(s)",
            "action_performed": "unauthorize",
        }

    @staticmethod
    def _export_to_excel(users):
        """Export users to an Excel spreadsheet"""
        data = ExportUserSerializer(users, many=True).data
        response = export_users_to_xlsx(data)
        logger.info(f"users.BULK_ACTIONS. Export {users.count()} users in xlsx")
        return response

    @staticmethod
    def _export_to_csv(users):
        """Export users to CSV file"""
        data = ExportUserSerializer(users, many=True).data
        response = export_users_to_csv(data)
        logger.info(f"users.BULK_ACTIONS. Export {users.count()} users in csv")
        return response
