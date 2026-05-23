from django.contrib import admin
from django.utils.html import format_html, mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(ModelAdmin):
    list_display = [
        "id",
        "level",
        "level_badge",
        "logger_name",
        "message_preview",
        "timestamp_display",
    ]
    list_filter = [
        "level",
        "timestamp",
    ]
    search_fields = [
        "message",
        "logger_name",
        "pathname",
        "exception",
    ]
    readonly_fields = ("id", "timestamp", "level", "logger_name", "message", "pathname", "line_no", "exception")
    list_per_page = 50
    
    fieldsets = (
        ("Log Information", {
            "fields": ("id", "timestamp", "level", "logger_name", "message")
        }),
        ("Location", {
            "fields": ("pathname", "line_no")
        }),
        ("Exception", {
            "fields": ("exception",)
        }),
    )
    
    @display(description="Level Badge")
    def level_badge(self, obj):
        colors = {
            "DEBUG": "bg-gray-100 text-gray-800",
            "INFO": "bg-blue-100 text-blue-800",
            "WARNING": "bg-yellow-100 text-yellow-800",
            "ERROR": "bg-red-100 text-red-800",
            "CRITICAL": "bg-red-200 text-red-900",
        }
        color_class = colors.get(obj.level.upper(), "bg-gray-100 text-gray-800")
        return format_html(
            '<span class="px-2 py-1 rounded text-xs font-semibold {}">{}</span>',
            color_class,
            obj.level,
        )
    
    @display(description="Message Preview")
    def message_preview(self, obj):
        if obj.message:
            preview = obj.message[:100] + "..." if len(obj.message) > 100 else obj.message
            return format_html('<span title="{}">{}</span>', obj.message, preview)
        return "-"
    
    @display(description="Timestamp", ordering="timestamp")
    def timestamp_display(self, obj):
        if obj.timestamp:
            return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return "-"
    
    class Meta:
        icon = "history"