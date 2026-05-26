from django.contrib import admin

from .models import PlagiarismReport


@admin.register(PlagiarismReport)
class PlagiarismReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "submission_a",
        "submission_b",
        "similarity_score",
        "flagged",
        "review_status",
        "reviewed_by",
        "created_at",
    )
    list_filter = ("flagged", "review_status", "created_at")
    search_fields = ("submission_a__id", "submission_b__id")
    readonly_fields = ("created_at", "updated_at", "reviewed_at")
