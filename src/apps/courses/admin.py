from django.contrib import admin
from unfold.admin import ModelAdmin
from unfold.decorators import display

from src.apps.courses.models import (
    Course,
    CourseEnrollment,
    CourseGroup,
    Category
)


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = [
        "id",
        "name",
        "category",
        "author",
        "is_active",
        "is_certificated",
        "free_order",
        "created_at_display",
    ]
    list_filter = [
        "is_active",
        "is_certificated",
        "free_order",
        "block_course_after_deadline",
        "allow_teachers_to_manage_tasks",
        "category",
        "created_at",
    ]
    search_fields = [
        "name",
        "description",
        "author__email",
        "author__first_name",
        "author__last_name",
        "category__name",
    ]
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
    list_select_related = ["category", "author"]
    raw_id_fields = ["author", "category"]
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("id", "name", "description", "category", "author", "image")
        }),
        ("Settings", {
            "fields": (
                "is_active",
                "is_certificated",
                "free_order",
                "allow_teachers_to_manage_tasks",
                "block_course_after_deadline",
            )
        }),
        ("Deadline", {
            "fields": ("deadline_to_finish_course",)
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
        icon = "school"


@admin.register(CourseGroup)
class CourseGroupAdmin(ModelAdmin):
    list_display = [
        "id",
        "name",
        "course",
        "students_limit",
        "is_active",
        "self_registration",
        "created_at_display",
    ]
    list_filter = [
        "is_active",
        "self_registration",
        "created_at",
    ]
    search_fields = [
        "name",
        "course__name",
        "registration_token",
    ]
    readonly_fields = ("id", "created_at", "updated_at", "registration_token")
    list_per_page = 25
    list_select_related = ["course"]
    raw_id_fields = ["course"]
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("id", "name", "course", "students_limit")
        }),
        ("Registration", {
            "fields": (
                "self_registration",
                "registration_token",
                "token_validity_hours",
                "token_validity_days",
                "token_expires_at",
            )
        }),
        ("Schedule", {
            "fields": ("days_of_week",)
        }),
        ("Status", {
            "fields": ("is_active",)
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
        icon = "groups"


@admin.register(CourseEnrollment)
class CourseEnrollmentAdmin(ModelAdmin):
    list_display = [
        "id",
        "user",
        "course",
        "group",
        "role",
        "enrolled_date_display",
    ]
    list_filter = [
        "role",
        "enrolled_date",
    ]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "course__name",
        "group__name",
    ]
    readonly_fields = ("id", "enrolled_date")
    list_per_page = 25
    list_select_related = ["user", "course", "group"]
    raw_id_fields = ["user", "course", "group"]
    
    fieldsets = (
        ("Enrollment Information", {
            "fields": ("id", "user", "course", "group", "role")
        }),
        ("Dates", {
            "fields": ("enrolled_date",)
        }),
    )
    
    @display(description="Enrolled Date", ordering="enrolled_date")
    def enrolled_date_display(self, obj):
        if obj.enrolled_date:
            return obj.enrolled_date.strftime("%Y-%m-%d %H:%M")
        return "-"
    
    class Meta:
        icon = "person_add"


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = [
        "id",
        "name",
        "parent_category",
        "created_at_display",
    ]
    list_filter = [
        "parent_category",
        "created_at",
    ]
    search_fields = [
        "name",
    ]
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
    list_select_related = ["parent_category"]
    raw_id_fields = ["parent_category"]
    
    fieldsets = (
        ("Category Information", {
            "fields": ("id", "name", "parent_category")
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
        icon = "category"
