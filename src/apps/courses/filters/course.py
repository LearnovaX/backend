import django_filters
from django.db.models import Q

from src.apps.courses.models import Course


class CourseFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")
    author = django_filters.NumberFilter(field_name="author_id")
    is_certificated = django_filters.BooleanFilter()
    free_order = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Course
        fields = ["category", "author", "is_certificated", "free_order"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(author__first_name__icontains=value)
            | Q(author__last_name__icontains=value)
            | Q(category__name__icontains=value)
        )
