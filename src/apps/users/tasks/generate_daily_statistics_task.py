import logging

from celery import shared_task
from django.utils import timezone

from src.apps.users.models import DailyUserStatistics

logger = logging.getLogger(__name__)


@shared_task(name="users.generate_daily_stats")
def generate_daily_stats():
    try:
        today = timezone.localdate()
        stats = DailyUserStatistics.generate_daily_snapshot(today)
        return {"status": "ok", "date": today.isoformat(), "total_users": stats.total_users}
    except Exception as e:
        logger.critical(msg=e)
