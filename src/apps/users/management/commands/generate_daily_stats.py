from django.core.management.base import BaseCommand
from django.utils import timezone

from src.apps.users.models import DailyUserStatistics


class Command(BaseCommand):
    help = "Generate daily user statistics snapshot"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Date in YYYY-MM-DD format (default: today)",
        )
        parser.add_argument(
            "--backfill",
            type=int,
            help="Backfill statistics for the last N days",
        )

    def handle(self, *args, **options):
        if options["backfill"]:
            # Backfill for the last N days
            for i in range(options["backfill"]):
                date = timezone.now().date() - timezone.timedelta(days=i)
                DailyUserStatistics.generate_daily_snapshot(date)
                self.stdout.write(self.style.SUCCESS(f"Generated statistics for {date}"))
        else:
            # Single day
            if options["date"]:
                from datetime import datetime

                date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            else:
                date = timezone.now().date()

            DailyUserStatistics.generate_daily_snapshot(date)
            self.stdout.write(self.style.SUCCESS(f"Generated statistics for {date}"))
