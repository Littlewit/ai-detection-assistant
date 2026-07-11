"""Celery 异步任务配置"""

from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_detect_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_concurrency=8,
)
