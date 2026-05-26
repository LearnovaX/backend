from django.core.management.base import BaseCommand
from django.conf import settings

try:
    from django_celery_beat.models import PeriodicTask, CrontabSchedule
except Exception:
    PeriodicTask = None
    CrontabSchedule = None


class Command(BaseCommand):
    help = "Sync CELERY_BEAT_SCHEDULE from settings into django-celery-beat DB (create/update only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--remove-missing",
            action="store_true",
            help="Remove PeriodicTasks that are not present in settings.CELERY_BEAT_SCHEDULE",
        )

    def handle(self, *args, **options):
        if PeriodicTask is None or CrontabSchedule is None:
            self.stderr.write("django-celery-beat is not installed or cannot be imported.")
            return

        schedule_map = getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {}

        existing = {pt.name: pt for pt in PeriodicTask.objects.all()}

        created = 0
        updated = 0

        for name, cfg in schedule_map.items():
            task = cfg.get("task")
            schedule = cfg.get("schedule")
            options = cfg.get("options") or {}
            args_ = cfg.get("args", [])
            kwargs_ = cfg.get("kwargs", {})

            if schedule is None:
                self.stdout.write(f"Skipping {name}: no schedule defined.")
                continue

            # Only handle crontab schedules here (common case in this project)
            if hasattr(schedule, "_orig_minute") or getattr(schedule, "__class__", None).__name__ == "crontab":
                # Extract fields from crontab object
                fields = {}
                for attr in ("minute", "hour", "day_of_week", "day_of_month", "month_of_year"):
                    val = getattr(schedule, attr, "*")
                    # crontab accepts ints or strings like '*/5'
                    fields[attr] = str(val)

                crontab_obj, _ = CrontabSchedule.objects.get_or_create(
                    minute=fields["minute"],
                    hour=fields["hour"],
                    day_of_week=fields["day_of_week"],
                    day_of_month=fields["day_of_month"],
                    month_of_year=fields["month_of_year"],
                    timezone=getattr(settings, "CELERY_TIMEZONE", None) or None,
                )

                pt = existing.get(name)
                pt_kwargs = {
                    "name": name,
                    "task": task,
                    "crontab": crontab_obj,
                    "args": json_dumps(args_),
                    "kwargs": json_dumps(kwargs_),
                    "enabled": options.get("enabled", True),
                    "queue": options.get("queue", None),
                }

                if pt is None:
                    PeriodicTask.objects.create(**pt_kwargs)
                    created += 1
                else:
                    # update fields if changed
                    changed = False
                    for k, v in pt_kwargs.items():
                        if getattr(pt, k) != v:
                            setattr(pt, k, v)
                            changed = True
                    if changed:
                        pt.save()
                        updated += 1
        if options.get("remove_missing"):
            to_remove = [pt for pname, pt in existing.items() if pname not in schedule_map]
            for pt in to_remove:
                pt.delete()

        self.stdout.write(f"sync_celerybeat: created={created} updated={updated}")


def json_dumps(obj):
    import json

    if obj is None:
        return "{}"
    try:
        return json.dumps(obj)
    except Exception:
        return str(obj)
