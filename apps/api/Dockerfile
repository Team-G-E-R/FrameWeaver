FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=api_src requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY --from=shared_pkg . /app/packages/shared
RUN pip install --no-cache-dir -e /app/packages/shared

COPY --from=api_src alembic.ini /app/alembic.ini
COPY --from=api_src alembic /app/alembic
COPY --from=api_src app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]