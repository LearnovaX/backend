from django.contrib import admin
from django.utils.html import format_html, mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = [
        "id",
        "title",
        "receiver",
        "sender",
        "is_read",
        "read_badge",
        "created_at_display",
    ]
    list_filter = [
        "is_read",
        "created_at",
    ]
    search_fields = [
        "title",
        "content",
        "receiver__email",
        "receiver__first_name",
        "receiver__last_name",
        "sender__email",
        "sender__first_name",
        "sender__last_name",
    ]
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
    list_select_related = ["receiver", "sender"]
    raw_id_fields = ["receiver", "sender"]
    
    fieldsets = (
        ("Notification Information", {
            "fields": ("id", "title", "content", "feedback")
        }),
        ("Recipients", {
            "fields": ("sender", "receiver", "is_read")
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    @display(description="Read Status")
    def read_badge(self, obj):
        if obj.is_read:
            return mark_safe(
                '<span class="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">Read</span>'
            )
        return mark_safe(
            '<span class="px-2 py-1 rounded text-xs font-semibold bg-red-100 text-red-800">Unread</span>'
        )
    
    @display(description="Created At", ordering="created_at")
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    class Meta:
        icon = "notifications"