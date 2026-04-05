# Re-export for celery CLI: `celery -A app.worker worker`
from app.worker.celery_app import celery_app as app  # noqa: F401
