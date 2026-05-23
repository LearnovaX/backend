import django_filters

from src.apps.assignments.models import Task


class TaskFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains", label="Task Name")
    description = django_filters.CharFilter(lookup_expr="icontains", label="Description")
    course = django_filters.NumberFilter(
        field_name="course__id", lookup_expr="exact", label="Course ID"
    )
    created_by = django_filters.CharFilter(
        field_name="created_by__username", lookup_expr="icontains", label="Created By"
    )
    number = django_filters.NumberFilter(lookup_expr="exact", label="Task Number")
    is_deleted = django_filters.BooleanFilter(field_name="is_deleted", label="Is Deleted")

    class Meta:
        model = Task
        fields = ["name", "description", "course", "created_by", "number", "is_deleted"]
