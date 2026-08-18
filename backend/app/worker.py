from celery import Celery

from app.core.config import settings

celery_app = Celery("autohire", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_soft_time_limit=300,
    task_time_limit=330,
    task_default_retry_delay=10,
    include=["app.tasks.resume_parse"],
)
