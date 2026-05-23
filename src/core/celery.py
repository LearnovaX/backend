# src/core/celery.py
import os

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.core.settings")

app = Celery("src.core")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover `<app>.tasks` for every app in INSTALLED_APPS
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# (Optional but helpful) explicitly import modules with tasks
app.conf.imports = (
    "src.apps.users.tasks",
    "src.apps.users.service.tasks",
    "src.apps.submissions.service",
    "src.apps.plagiarism.tasks",
)

# Clean up a stray route pattern you had (this was a no-op/mismatch)
app.conf.update(
    task_routes={
        "src.apps.users.service.*": {"queue": "celery"},
        "src.apps.users.tasks.*": {"queue": "celery"},
        "plagiarism.*": {"queue": "celery"},
    },
    task_default_queue="celery",
    task_create_missing_queues=True,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
