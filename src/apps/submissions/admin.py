from django.contrib import admin
from django.utils.html import format_html, mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models.answers import Answer
from .models.files import AnswerFile


@admin.register(Answer)
class AnswerAdmin(ModelAdmin):
    list_display = [
        "id",
        "task",
        "user",
        "status",
        "plagiarism_status",
        "status_badge",
        "created_at_display",
    ]
    list_filter = [
        "status",
        "plagiarism_status",
        "created_at",
    ]
    search_fields = [
        "task__name",
        "user__email",
        "user__first_name",
        "user__last_name",
        "description",
    ]
    readonly_fields = ("id", "created_at", "updated_at", "extracted_text", "analyzed_at")
    list_per_page = 25
    list_select_related = ["task", "task__course", "user"]
    raw_id_fields = ["task", "user"]
    
    fieldsets = (
        ("Answer Information", {
            "fields": ("id", "task", "user", "description", "status")
        }),
        ("Plagiarism Analysis", {
            "fields": ("plagiarism_status", "extracted_text", "analyzed_at")
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    @display(description="Status Badge")
    def status_badge(self, obj):
        colors = {
            "in_review": "bg-yellow-100 text-yellow-800",
            "approved": "bg-green-100 text-green-800",
            "have_flaws": "bg-orange-100 text-orange-800",
            "rejected": "bg-red-100 text-red-800",
        }
        color_class = colors.get(obj.status, "bg-gray-100 text-gray-800")
        return format_html(
            '<span class="px-2 py-1 rounded text-xs font-semibold {}">{}</span>',
            color_class,
            obj.get_status_display(),
        )
    
    @display(description="Created At", ordering="created_at")
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    class Meta:
        icon = "description"


@admin.register(AnswerFile)
class AnswerFileAdmin(ModelAdmin):
    list_display = [
        "id",
        "answer",
        "original_name",
        "size_display",
        "content_type",
        "created_at_display",
    ]
    list_filter = [
        "content_type",
        "created_at",
    ]
    search_fields = [
        "original_name",
        "answer__task__name",
        "answer__user__email",
    ]
    readonly_fields = ("id", "created_at", "updated_at", "original_name", "size", "content_type")
    list_per_page = 25
    list_select_related = ["answer", "answer__task", "answer__user"]
    raw_id_fields = ["answer"]
    
    fieldsets = (
        ("File Information", {
            "fields": ("id", "answer", "file", "original_name", "size", "content_type")
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    @display(description="Size")
    def size_display(self, obj):
        if obj.size:
            for unit in ['B', 'KB', 'MB', 'GB']:
                if obj.size < 1024.0:
                    return f"{obj.size:.1f} {unit}"
                obj.size /= 1024.0
            return f"{obj.size:.1f} TB"
        return "-"
    
    @display(description="Created At", ordering="created_at")
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    class Meta:
        icon = "attach_file"
