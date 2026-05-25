import logging

from django.contrib import admin
from django import forms
from django.utils.html import format_html, mark_safe
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from unfold.admin import ModelAdmin
from unfold.decorators import display

from .service import send_activation_invite
from .models import User, UserProfile

logger = logging.getLogger(__name__)


def _ensure_user_profile(user: User) -> None:
    try:
        UserProfile.objects.get_or_create(user=user)
    except IntegrityError as e:
        logger.warning(
            "users.admin. Failed to ensure profile for user=%s error=%s",
            user.pk,
            e,
        )


class UserAdminForm(forms.ModelForm):
    let_user_set_password = forms.BooleanField(
        label=_("Let user set password"),
        required=False,
        initial=True,
        help_text=_(
            "If checked, an invitation link will be sent to the user. "
            "If unchecked, you can set a password manually."
        ),
        widget=forms.CheckboxInput(
            attrs={
                "class": "user-password-toggle user-password-toggle--fancy",
                "data-toggle": "password-invite",
            }
        ),
    )

    raw_password = forms.CharField(
        label=_("Set password"),
        required=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "vTextField password-field",
                "placeholder": _("Enter password for the user"),
                "autocomplete": "new-password",
            }
        ),
        help_text=_("Enter a raw password. Django will automatically hash it before saving."),
    )

    class Meta:
        model = User
        fields = "__all__"
        # We don't want the built-in password field in the admin form,
        # we handle it via raw_password / let_user_set_password
        exclude = ("password",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # For existing users: hide the password controls (only for creation)
        if self.instance.pk:
            self.fields["let_user_set_password"].widget = forms.HiddenInput()
            self.fields["raw_password"].widget = forms.HiddenInput()
            self.fields["let_user_set_password"].required = False
            self.fields["raw_password"].required = False

    def clean(self):
        cleaned_data = super().clean()

        # Only enforce logic for new users
        if not self.instance.pk:
            let_user_set = cleaned_data.get("let_user_set_password", True)
            raw_password = cleaned_data.get("raw_password")

            if not let_user_set and not raw_password:
                raise ValidationError(
                    {
                        "raw_password": _(
                            "Please enter a password or check 'Let user set password'."
                        )
                    }
                )

            if let_user_set and raw_password:
                raise ValidationError(
                    _(
                        "You cannot set both 'Let user set password' and provide a manual password. "
                        "Please choose one option."
                    )
                )

        return cleaned_data

    def save(self, commit=True):
        user: User = super().save(commit=False)

        is_new_user = not self.instance.pk

        if is_new_user:
            let_user_set = self.cleaned_data.get("let_user_set_password", True)
            raw_password = self.cleaned_data.get("raw_password")

            if let_user_set:
                # User will set password via invite link
                user.set_unusable_password()
                user.save()
                _ensure_user_profile(user)

                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                send_activation_invite(user.email, user.first_name, uid, token)
            else:
                # Admin sets password directly
                user.password = make_password(raw_password)
                user.must_set_password = False
                user.email_verified = True
                user.save()
                _ensure_user_profile(user)

        if commit:
            if not is_new_user:
                user.save()
            self.save_m2m()

        return user



@admin.register(User)
class UserAdmin(ModelAdmin):
    form = UserAdminForm

    list_display = [
        "id",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "email_verified",
        "created_at_display",
    ]
    list_filter = [
        "role",
        "is_active",
        "email_verified",
        "is_deleted",
        "mfa_enabled",
        "date_joined",
    ]
    search_fields = [
        "email",
        "first_name",
        "last_name",
        "google_id",
    ]
    readonly_fields = ("id", "date_joined", "last_login")
    list_per_page = 25
    list_select_related = True

    fieldsets = (
        (_("Personal Information"), {
            "fields": ("id", "email", "first_name", "last_name", "google_id"),
        }),
        (_(
            "Password Settings"),
            {
            "fields": ("let_user_set_password", "raw_password"),
            "classes": ("password-settings",),  # 👈 hook for styling
            "description": mark_safe(
                '<div class="password-info">'
                '<strong>⚠️ Password Configuration (New Users Only)</strong><br>'
                '• <strong>Let user set password (checked):</strong> '
                'User will receive an invitation email to set their own password.<br>'
                '• <strong>Let user set password (unchecked):</strong> '
                'You can set a password manually below. Django will hash it automatically.'
                "</div>"
            ),
        }),
        (_("Status"), {
            "fields": (
                "is_active",
                "email_verified",
                "must_set_password",
                "mfa_enabled",
                "is_deleted",
                "role",
            ),
        }),
        (_("Dates"), {
            "fields": ("date_joined", "last_login"),
        }),
    )

    @display(description=_("Created At"), ordering="date_joined")
    def created_at_display(self, obj):
        if obj.date_joined:
            return obj.date_joined.strftime("%Y-%m-%d %H:%M")
        return "-"

    class Meta:
        icon = "people"


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "phone_number",
        "birth_date",
        "company",
        "interface_language",
        "profile_edit_blocked",
        "updated_at_display",
    ]
    list_filter = [
        "interface_language",
        "profile_edit_blocked",
        "updated_at",
    ]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "phone_number",
        "company",
    ]
    readonly_fields = ("id", "updated_at")
    list_per_page = 25
    list_select_related = ["user"]
    raw_id_fields = ["user"]

    fieldsets = (
        (_("User"), {
            "fields": ("id", "user"),
        }),
        (_("Personal Information"), {
            "fields": ("middle_name", "birth_date", "phone_number", "company", "profile_photo"),
        }),
        (_("Settings"), {
            "fields": ("interface_language", "timezone", "profile_edit_blocked"),
        }),
        (_("Deactivation"), {
            "fields": ("deactivation_time", "days_to_delete_after_deactivation"),
        }),
        (_("Dates"), {
            "fields": ("updated_at",),
        }),
    )

    @display(description=_("Updated At"), ordering="updated_at")
    def updated_at_display(self, obj):
        if obj.updated_at:
            return obj.updated_at.strftime("%Y-%m-%d %H:%M")
        return "-"

    class Meta:
        icon = "person"
