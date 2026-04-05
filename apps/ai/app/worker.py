# Re-export for celery CLI: `celery -A app.worker worker`
# Celery CLI looks for an attribute named `celery` or any Celery instance
from app.worker.celery_app import celery_app as celery  # noqa: F401
