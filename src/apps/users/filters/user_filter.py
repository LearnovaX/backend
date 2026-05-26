import django_filters
from django.db.models import Q

from ..models import User


class UserFilter(django_filters.FilterSet):
    group_ids = django_filters.BaseInFilter(field_name="enrollments__group_id", lookup_expr="in")
    user_status = django_filters.CharFilter(method="filter_user_status")
    search = django_filters.CharFilter(method="filter_search")
    role = django_filters.CharFilter(field_name="role")
    is_active = django_filters.BooleanFilter()
    email_verified = django_filters.BooleanFilter()
    must_set_password = django_filters.BooleanFilter()
    has_deactivation_time = django_filters.BooleanFilter(method="filter_has_deactivation_time")

    ordering = django_filters.OrderingFilter(
        fields=[
            ("first_name", "first_name"),
            ("last_name", "last_name"),
            ("email", "email"),
            ("date_joined", "date_joined"),
            ("last_login", "last_login"),
            ("role", "role"),
            ("is_active", "is_active"),
            ("email_verified", "email_verified"),
        ]
    )

    class Meta:
        model = User
        fields = []

    def filter_user_status(self, queryset, name, value):
        if value == "authorized":
            return queryset.filter(
                is_active=True,
                must_set_password=False,
                email_verified=True,
            )
        elif value == "not_authorized":
            return queryset.filter(is_active=True).filter(
                Q(must_set_password=True) | Q(email_verified=False)
            )
        elif value == "deactivated":
            return queryset.filter(is_active=False)
        return queryset

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(first_name__icontains=value)
            | Q(last_name__icontains=value)
            | Q(email__icontains=value)
            | Q(profile__phone_number__icontains=value)
        )

    def filter_has_deactivation_time(self, queryset, name, value: bool):
        return queryset.filter(profile__deactivation_time__isnull=not value)
