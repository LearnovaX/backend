from django.contrib import admin
from unfold.sites import UnfoldAdminSite
from unfold.admin import ModelAdmin
from django_celery_beat.models import (
    PeriodicTask,
    IntervalSchedule,
    CrontabSchedule,
    ClockedSchedule,
    SolarSchedule
)


class IntervalScheduleAdmin(ModelAdmin):
    list_display = ('__str__', 'every', 'period')
    list_filter = ('period',)
    search_fields = ('every',)
    ordering = ('every',)

    fieldsets = (
        (None, {
            'fields': ('every', 'period'),
            'classes': ('unfold',),
        }),
    )

    help_texts = {
        'every': 'The number of time units between task executions.',
        'period': 'The time unit for the interval (e.g., seconds, minutes).',
    }


class CrontabScheduleAdmin(ModelAdmin):
    list_display = ('__str__', 'minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year')
    list_filter = ('month_of_year', 'day_of_week')
    search_fields = ('minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year')

    fieldsets = (
        ('Time', {
            'fields': ('minute', 'hour'),
            'classes': ('unfold',),
        }),
        ('Date', {
            'fields': ('day_of_week', 'day_of_month', 'month_of_year'),
            'classes': ('unfold',),
        }),
    )

    help_texts = {
        'minute': 'Minute (0-59). Use * for every minute.',
        'hour': 'Hour (0-23). Use * for every hour.',
        'day_of_week': 'Day of week (0-6, Sunday=0). Use * for every day.',
        'day_of_month': 'Day of month (1-31). Use * for every day.',
        'month_of_year': 'Month (1-12). Use * for every month.',
    }


class ClockedScheduleAdmin(ModelAdmin):
    list_display = ('__str__', 'clocked_time')
    list_filter = ('clocked_time',)
    search_fields = ('clocked_time',)


class SolarScheduleAdmin(ModelAdmin):
    list_display = ('__str__', 'event', 'latitude', 'longitude')
    list_filter = ('event',)
    search_fields = ('event', 'latitude', 'longitude')


class PeriodicTaskAdmin(ModelAdmin):
    list_display = ('name', 'task', 'enabled', 'last_run_at', 'total_run_count')
    list_filter = ('enabled', 'one_off', 'task')
    search_fields = ('name', 'task')
    ordering = ('name',)

    fieldsets = (
        (None, {
            'fields': ('name', 'task', 'description'),
            'classes': ('unfold',),
        }),
        ('Schedule', {
            'fields': ('interval', 'crontab', 'solar', 'clocked'),
            'description': 'Select one type of schedule. Only one should be chosen.',
            'classes': ('unfold',),
        }),
        ('Arguments', {
            'fields': ('args', 'kwargs'),
            'classes': ('collapse', 'unfold'),
        }),
        ('Queue & Routing', {
            'fields': ('queue', 'exchange', 'routing_key', 'headers', 'priority'),
            'classes': ('collapse', 'unfold'),
        }),
        ('Timing & Control', {
            'fields': ('expires', 'expire_seconds', 'one_off', 'start_time', 'enabled'),
            'classes': ('unfold',),
        }),
    )

    readonly_fields = ('last_run_at', 'total_run_count', 'date_changed')

    help_texts = {
        'name': 'A human-readable name for this task.',
        'task': 'The name of the task function to execute.',
        'interval': 'For interval-based scheduling.',
        'crontab': 'For cron-based scheduling.',
        'solar': 'For solar event-based scheduling.',
        'clocked': 'For one-time scheduling at a specific time.',
        'args': 'JSON list of positional arguments for the task.',
        'kwargs': 'JSON dict of keyword arguments for the task.',
        'queue': 'The queue to send the task to.',
        'enabled': 'Whether this task is active.',
    }


class CustomAdminSite(UnfoldAdminSite):
    """Custom admin site with enhanced features"""

    site_header = "Your Blog Admin"
    site_title = "Blog Admin Portal"
    index_title = "Welcome to Your Blog Administration"

    def each_context(self, request):
        context = super().each_context(request)

        # Add custom dashboard statistics
        if request.user.is_authenticated:
            from apps.posts.models import Post
            from apps.users.models import User

            context.update({
                'custom_stats': {
                    'total_posts': Post.objects.count(),
                    'published_posts': Post.objects.filter(status='published').count(),
                    'draft_posts': Post.objects.filter(status='draft').count(),
                    'total_users': User.objects.count(),
                    'active_users': User.objects.filter(is_active=True).count(),
                    'verified_users': User.objects.filter(email_verified=True).count(),
                }
            })

        return context


# Optional: Replace the default admin site
# admin.site = CustomAdminSite()
# admin.site.__class__ = CustomAdminSite


def dashboard_callback(request, context):
    """
    Add custom dashboard statistics and widgets
    """
    from apps.posts.models import Post
    from apps.users.models import User
    from django.utils.timezone import now
    from datetime import timedelta

    # Recent activity
    recent_posts = Post.objects.order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-date_joined')[:5]

    # Statistics for last 30 days
    thirty_days_ago = now() - timedelta(days=30)

    context.update({
        "custom_dashboard": {
            "recent_posts": recent_posts,
            "recent_users": recent_users,
            "stats_30_days": {
                "new_posts": Post.objects.filter(created_at__gte=thirty_days_ago).count(),
                "new_users": User.objects.filter(date_joined__gte=thirty_days_ago).count(),
                "published_posts": Post.objects.filter(
                    status='published',
                    published_at__gte=thirty_days_ago
                ).count(),
            }
        }
    })

    return context


# Register Celery Beat models with custom admin
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(PeriodicTask)

admin.site.register(IntervalSchedule, IntervalScheduleAdmin)
admin.site.register(CrontabSchedule, CrontabScheduleAdmin)
admin.site.register(ClockedSchedule, ClockedScheduleAdmin)
admin.site.register(SolarSchedule, SolarScheduleAdmin)
admin.site.register(PeriodicTask, PeriodicTaskAdmin)
