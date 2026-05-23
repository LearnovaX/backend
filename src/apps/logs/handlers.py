import logging

from django.utils import timezone


class DatabaseHandler(logging.Handler):
    def emit(self, record):
        try:
            from src.apps.logs.models import LogEntry

            LogEntry.objects.create(
                timestamp=timezone.now(),
                level=record.levelname,
                logger_name=record.name,
                message=self.format(record),
                pathname=record.pathname,
                line_no=record.lineno,
                exception=record.exc_info if record.exc_info else None,
            )
        except Exception:
            pass
