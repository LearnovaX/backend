from django.contrib import admin
from django.utils.html import format_html, mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Grade


@admin.register(Grade)
class GradeAdmin(ModelAdmin):
    list_display = [
        "id",
        "answer",
        "score",
        "max_score",
        "percentage_display",
        "letter_grade_display",
        "graded_by",
        "created_at_display",
    ]
    list_filter = [
        "created_at",
        "graded_by",
    ]
    search_fields = [
        "answer__user__email",
        "answer__user__first_name",
        "answer__user__last_name",
        "answer__task__name",
        "graded_by__email",
        "graded_by__first_name",
        "graded_by__last_name",
        "feedback_text",
    ]
    readonly_fields = ("id", "created_at", "updated_at", "percentage", "letter_grade")
    list_per_page = 25
    list_select_related = ["answer", "answer__user", "answer__task", "graded_by"]
    raw_id_fields = ["answer", "graded_by"]
    
    fieldsets = (
        ("Grade Information", {
            "fields": ("id", "answer", "graded_by")
        }),
        ("Scores", {
            "fields": ("score", "max_score", "percentage", "letter_grade")
        }),
        ("Feedback", {
            "fields": ("feedback_text",)
        }),
        ("Dates", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    @display(description="Percentage", ordering="score")
    def percentage_display(self, obj):
        percentage = obj.percentage
        color = "green" if percentage >= 70 else "orange" if percentage >= 50 else "red"
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            percentage
        )
    
    @display(description="Letter Grade", ordering="score")
    def letter_grade_display(self, obj):
        grade = obj.letter_grade
        color = "green" if grade in ["A", "B"] else "orange" if grade == "C" else "red"
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 1.2em;">{}</span>',
            color,
            grade
        )
    
    @display(description="Created At", ordering="created_at")
    def created_at_display(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    class Meta:
        icon = "grade"
