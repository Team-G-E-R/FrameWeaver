import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import MetaData, Table, create_engine, func, select, update

from shared.contracts import build_result_v1
from worker_app import app


def _pg_url_sync() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def _job_root_dir(job_id: str) -> Path:
    base = os.environ.get("JOB_DATA_DIR", "/data/jobs")
    return Path(base) / job_id


def _extract_prompt(params: dict) -> str:
    if not isinstance(params, dict):
        return ""
    v = params.get("prompt", "")
    return v if isinstance(v, str) else ""


def _should_wait(prompt: str) -> bool:
    return "wait" in prompt.lower()


def _sleep_for_prompt(prompt: str) -> float:
    low = prompt.lower().strip()
    if "wait:" in low:
        try:
            tail = low.split("wait:", 1)[1].strip()
            return max(0.0, min(60.0, float(tail)))
        except Exception:
            return 2.0
    return 2.0


def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


@app.task(name="jobs.run")
def run_job(job_id: str) -> None:
    jid = str(uuid.UUID(job_id))
    engine = create_engine(_pg_url_sync(), pool_pre_ping=True)

    started = time.perf_counter()

    try:
        with engine.begin() as conn:
            metadata = MetaData()
            jobs = Table("jobs", metadata, autoload_with=conn)

            row = conn.execute(
                select(jobs.c.type, jobs.c.params).where(jobs.c.job_id == jid)
            ).mappings().first()

            if not row:
                raise RuntimeError("Job not found")

            job_type = row.get("type")
            params = row.get("params")
            prompt = _extract_prompt(params)

            conn.execute(
                update(jobs)
                .where(jobs.c.job_id == jid)
                .values(status="running", updated_at=func.now())
            )

        if _should_wait(prompt):
            time.sleep(_sleep_for_prompt(prompt))

        root = _job_root_dir(jid)
        out_dir = root / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        preview_path = out_dir / "preview.txt"
        preview_path.write_text(
            f"stub generator ok\njob_id={jid}\ntype={job_type}\nprompt={prompt}\n",
            encoding="utf-8",
        )

        duration_ms = int((time.perf_counter() - started) * 1000)

        result_payload = build_result_v1(
            kind=str(job_type),
            engine="stub",
            artifacts={
                "preview": "out/preview.txt",
            },
            meta={
                "prompt": prompt,
                "duration_ms": duration_ms,
            },
        )

        _write_json_atomic(out_dir / "result.json", result_payload)

        with engine.begin() as conn:
            metadata = MetaData()
            jobs = Table("jobs", metadata, autoload_with=conn)

            conn.execute(
                update(jobs)
                .where(jobs.c.job_id == jid)
                .values(
                    status="succeeded",
                    result=result_payload,
                    error=None,
                    updated_at=func.now(),
                )
            )

    except Exception as e:
        err = f"{type(e).__name__}: {e}"

        with engine.begin() as conn:
            metadata = MetaData()
            jobs = Table("jobs", metadata, autoload_with=conn)

            conn.execute(
                update(jobs)
                .where(jobs.c.job_id == jid)
                .values(status="failed", error=err[:1000], updated_at=func.now())
            )

        raise

    finally:
        engine.dispose()