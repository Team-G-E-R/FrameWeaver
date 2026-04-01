FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY apps/translation_service/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy==1.26.4 && \
    pip install --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu \
      torch==2.1.2 torchvision==0.16.2 && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY apps/translation_service/app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]