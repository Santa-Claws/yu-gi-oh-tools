from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "yugioh",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.worker.tasks.import_tasks",
        "app.worker.tasks.scrape_tasks",
        "app.worker.tasks.embed_tasks",
        "app.worker.tasks.scrape_meta_decks_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    # Re-import cards weekly
    "import-cards-weekly": {
        "task": "app.worker.tasks.import_tasks.import_cards_task",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),
    },
    # Scrape meta sources daily
    "scrape-meta-daily": {
        "task": "app.worker.tasks.scrape_tasks.scrape_all_sources_task",
        "schedule": crontab(hour=4, minute=0),
    },
    # Re-embed new cards nightly
    "embed-cards-nightly": {
        "task": "app.worker.tasks.embed_tasks.embed_cards_task",
        "schedule": crontab(hour=5, minute=0),
    },
    # Refresh meta deck lists daily
    "scrape-meta-decks-daily": {
        "task": "scrape_meta_decks_task",
        "schedule": crontab(hour=6, minute=0),
    },
}
