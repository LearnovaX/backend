import django_filters
from django.db.models import Q

from src.apps.courses.models import CourseGroup


class CourseGroupFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method="filter_search")
    is_active = django_filters.CharFilter(method="filter_is_active")
    ordering = django_filters.OrderingFilter(
        fields=(
            ("created_at", "created_at"),
            ("name", "name"),
        ),
        field_labels={
            "created_at": "Created At",
            "name": "Name",
        },
    )

    class Meta:
        model = CourseGroup
        fields = ["is_active"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(course__name__icontains=value)
            | Q(members__role="teacher", members__user__first_name__icontains=value)
            | Q(members__role="teacher", members__user__last_name__icontains=value)
            | Q(members__role="teacher", members__user__email__icontains=value)
        ).distinct()

    def filter_is_active(self, queryset, name, value: str):
        val = value.strip().lower()
        if val in {"true", "1", "yes"}:
            return queryset.filter(is_active=True)
        elif val in {"false", "0", "no"}:
            return queryset.filter(is_active=False)
        elif val == "all":
            return queryset
        return queryset.filter(is_active=True)  # fallback
