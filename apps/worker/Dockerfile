FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=worker_src requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY --from=shared_pkg . /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

COPY --from=worker_src worker_app.py /app/worker_app.py
COPY --from=worker_src tasks.py /app/tasks.py
COPY --from=worker_src webui_client.py /app/webui_client.py

CMD ["celery", "-A", "worker_app", "worker", "-l", "info", "-Q", "celery", "--concurrency=1"]