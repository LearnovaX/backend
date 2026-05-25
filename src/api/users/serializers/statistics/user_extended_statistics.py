from rest_framework import serializers


class HistoricalStatisticsSerializer(serializers.Serializer):
    """Serializer for historical statistics data for charts"""

    def to_representation(self, queryset):
        data = {
            "dates": [],
            "total_users": [],
            "active_users": [],
            "authorized_users": [],
            "not_authorized_users": [],
            "new_users_daily": [],
            "deactivated_users_daily": [],
            "profile_completion_rate": [],
            "role_distribution_over_time": [],
            "enrollments": [],
        }

        for stat in queryset:
            data["dates"].append(stat.date.isoformat())
            data["total_users"].append(stat.total_users)
            data["active_users"].append(stat.active_users)
            data["authorized_users"].append(stat.authorized_users)
            data["not_authorized_users"].append(stat.not_authorized_users)
            data["new_users_daily"].append(stat.new_users_today)
            data["deactivated_users_daily"].append(stat.deactivated_users_today)
            data["profile_completion_rate"].append(round(stat.profile_completion_rate, 2))
            data["role_distribution_over_time"].append(
                {"date": stat.date.isoformat(), "roles": stat.role_distribution}
            )
            data["enrollments"].append(stat.total_enrollments)

        return data
