# Game Assets Generator
## VMP – Stage 1 (Pre SD-WebUI Integration)

Дата фиксации: 2026-03-01  
Статус: MVP backend стабилен, stub-generator работает

---

# 1. Архитектура MVP

## Backend
- FastAPI
- PostgreSQL 16
- Redis 7
- Celery worker (concurrency=1)
- SQLAlchemy async (API) + sync (worker)
- Alembic migrations
- Docker Compose

## Статусы job
- queued
- running
- succeeded
- failed

Одна активная job на пользователя enforced на уровне API.

---

# 2. Файловый контракт

DATA volume (docker named volume):
/data

Jobs:
/data/jobs/<job_id>/
    /in
    /out

Stub-generator создаёт:
/data/jobs/<job_id>/out/preview.txt

---

# 3. Result Contract (JSONB)

Пример result:

{
  "kind": "sprites",
  "files": [
    {
      "path": "out/preview.txt",
      "mime": "text/plain"
    }
  ],
  "meta": {
    "prompt": "...",
    "generator": "stub",
    "duration_ms": 65
  }
}

---

# 4. Worker Behavior

apps/worker/tasks.py:

- Получает job_id
- Меняет статус → running
- Выполняет stub генератор
- Создаёт директорию /data/jobs/<job_id>/out
- Пишет preview.txt
- Обновляет result JSONB
- Ставит succeeded
- При ошибке → failed + error

---

# 5. Docker Infrastructure

## Services

- postgres (volume pgdata)
- redis
- api
- worker

DATA хранится в docker named volume:
gameassetsgenerator_data

---

# 6. Миграции

Alembic выполняется при старте API контейнера:
alembic upgrade head

Таблица:
jobs (UUID PK)

---

# 7. Проверено

✔ Создание job  
✔ Блокировка второй job (409)  
✔ Завершение job  
✔ Повторное создание после завершения  
✔ Запись файлов в /data/jobs  
✔ Получение result через API  

Smoke test:
workerTest.ps1 → ALL TESTS PASSED

---

# 8. Текущие ограничения

- Нет реальной модели
- Нет SD WebUI
- Нет авторизации (JWT пока dev-mode)
- Нет прогресса job
- Нет стриминга файлов
- Нет TTL-cleanup

---

# 9. Следующий этап (Stage 2)

Интеграция Stable Diffusion WebUI (CPU mode):

- engine switch: stub | sd_webui
- SD_WEBUI_BASE_URL
- txt2img → save png
- result.files → image/png
- meta: seed, steps, width, height

---

# 10. Важно

dev-time endpoint mark_failed существует  
→ ОБЯЗАТЕЛЬНО удалить перед релизом.

---

Stage 1 считается завершённым.