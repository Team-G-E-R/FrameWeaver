import os
from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", BROKER_URL)

celery_app = Celery(
    "api_client",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
)

# опционально, но полезно: единый дефолт
celery_app.conf.update(
    task_default_queue="celery",
)