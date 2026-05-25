from django.contrib import admin
from django.utils.html import format_html, mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import ChatRoom, Message


@admin.register(ChatRoom)
class ChatRoomAdmin(ModelAdmin):
    list_display = [
        "id",
        "teacher",
        "student",
        "course",
        "is_active",
        "active_badge",
        "created_at_display",
    ]
    list_filter = [
        "is_active",
        "created_at",
        "course",
    ]
    search_fields = [
        "teacher__email",
        "teacher__first_name",
        "teacher__last_name",
        "student__email",
        "student__first_name",
        "student__last_name",
        "course__name",
    ]
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
    list_select_related = ["teacher", "student", "course"]
    raw_id_fields = ["teacher", "student", "course"]
    
    fieldsets = (
        ("Chat Room Information", {
            "fields": ("id", "teacher", "student", "course", "is_active")
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    @display(description="Active Status")
    def active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span class="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">Active</span>'
            )
        return mark_safe(
            '<span class="px-2 py-1 rounded text-xs font-semibold bg-gray-100 text-gray-800">Inactive</span>'
        )
    
    @display(description="Created At", ordering="created_at")
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    class Meta:
        icon = "chat"


@admin.register(Message)
class MessageAdmin(ModelAdmin):
    list_display = [
        "id",
        "chat_room",
        "sender",
        "content_preview",
        "is_read",
        "read_badge",
        "has_file",
        "created_at_display",
    ]
    list_filter = [
        "is_read",
        "created_at",
    ]
    search_fields = [
        "content",
        "sender__email",
        "sender__first_name",
        "sender__last_name",
        "chat_room__teacher__email",
        "chat_room__student__email",
    ]
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
    list_select_related = ["chat_room", "sender"]
    raw_id_fields = ["chat_room", "sender"]
    
    fieldsets = (
        ("Message Information", {
            "fields": ("id", "chat_room", "sender", "content", "file", "is_read")
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    @display(description="Content Preview")
    def content_preview(self, obj):
        if obj.content:
            preview = obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
            return format_html('<span title="{}">{}</span>', obj.content, preview)
        return "-"
    
    @display(description="Read Status")
    def read_badge(self, obj):
        if obj.is_read:
            return mark_safe(
                '<span class="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-800">Read</span>'
            )
        return mark_safe(
            '<span class="px-2 py-1 rounded text-xs font-semibold bg-red-100 text-red-800">Unread</span>'
        )
    
    @display(description="Has File", boolean=True)
    def has_file(self, obj):
        return bool(obj.file)
    
    @display(description="Created At", ordering="created_at")
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    class Meta:
        icon = "message"