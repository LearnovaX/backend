from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Task


@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = [
        "id",
        "number",
        "name",
        "course",
        "created_by",
        "enable_context_menu_for_students",
        "allow_resubmitting_task",
        "created_at_display",
    ]
    list_filter = [
        "enable_context_menu_for_students",
        "allow_resubmitting_task",
        "created_at",
        "course",
    ]
    search_fields = [
        "name",
        "description",
        "course__name",
        "created_by__email",
        "created_by__first_name",
        "created_by__last_name",
    ]
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
    list_select_related = ["course", "created_by"]
    raw_id_fields = ["course", "created_by"]
    
    fieldsets = (
        ("Task Information", {
            "fields": ("id", "number", "name", "description", "course", "created_by")
        }),
        ("Media", {
            "fields": ("image", "video", "file")
        }),
        ("Settings", {
            "fields": (
                "enable_context_menu_for_students",
                "allow_resubmitting_task",
            )
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    @display(description="Created At", ordering="created_at")
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    class Meta:
        icon = "assignment"