from celery import Celery
import os


redis_host = os.getenv("REDIS_HOST", "redis")
redis_port = os.getenv("REDIS_PORT", "6379")
broker_url = f"redis://{redis_host}:{redis_port}/0"

app = Celery("worker", broker=broker_url, backend=broker_url)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

import tasks  # noqa: F401