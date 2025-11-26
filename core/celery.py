import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("celery")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Heroku-specific optimizations
app.conf.update(
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

app.autodiscover_tasks()
