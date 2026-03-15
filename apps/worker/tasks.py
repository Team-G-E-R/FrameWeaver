import json
import os
import time
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, Dict

from PIL import Image
from sqlalchemy import MetaData, Table, create_engine, func, select, update

from shared.contracts import build_result_v1
from webui_client import SdWebuiClient, get_sd_webui_url
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


def _extract_int(params: dict, key: str, default: int) -> int:
    if not isinstance(params, dict):
        return default
    v = params.get(key, default)
    try:
        v = int(v)
    except Exception:
        return default
    return v


def _extract_str(params: dict, key: str, default: str) -> str:
    if not isinstance(params, dict):
        return default
    v = params.get(key, default)
    return v if isinstance(v, str) else default


def _extract_float(params: dict, key: str, default: float) -> float:
    if not isinstance(params, dict):
        return default
    v = params.get(key, default)
    try:
        return float(v)
    except Exception:
        return default


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


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


def _resize_png_bytes_nearest(png_bytes: bytes, width: int, height: int) -> bytes:
    with Image.open(BytesIO(png_bytes)) as img:
        img = img.convert("RGBA")

        if img.width == width and img.height == height:
            out = BytesIO()
            img.save(out, format="PNG")
            return out.getvalue()

        resized = img.resize((width, height), Image.Resampling.NEAREST)
        out = BytesIO()
        resized.save(out, format="PNG")
        return out.getvalue()


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

            if isinstance(params, dict) and "size" in params and ("width" not in params and "height" not in params):
                s = _clamp(_extract_int(params, "size", 512), 64, 1024)
                params = dict(params)
                params["width"] = s
                params["height"] = s

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

        requested_width = _clamp(_extract_int(params, "width", 512), 64, 1024)
        requested_height = _clamp(_extract_int(params, "height", 512), 64, 1024)
        steps = _clamp(_extract_int(params, "steps", 20), 1, 50)

        negative_prompt = _extract_str(params, "negative_prompt", "")
        if not negative_prompt.strip():
            negative_prompt = (
                "text, watermark, logo, signature, letters, numbers, blurry, noise, "
                "jpeg artifacts, deformed, bad anatomy, extra limbs, extra fingers, "
                "cropped, out of frame, background scene, realistic, 3d render"
            )

        sampler_name = _extract_str(params, "sampler_name", "Euler a")
        seed = 12345

        cfg_scale = _extract_float(params, "cfg_scale", 5.0)
        if cfg_scale < 1.0:
            cfg_scale = 1.0
        if cfg_scale > 20.0:
            cfg_scale = 20.0

        generation_width = 512
        generation_height = 512

        webui_payload: Dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler_name,
            "seed": seed,
            "width": generation_width,
            "height": generation_height,
            "batch_size": 1,
            "n_iter": 1,
            "restore_faces": False,
            "tiling": False,
        }

        client = SdWebuiClient(get_sd_webui_url())
        res = client.txt2img(webui_payload, timeout_s=1800)

        original_png_path = out_dir / "result_512.png"
        original_png_path.write_bytes(res.png_bytes)

        final_png_bytes = _resize_png_bytes_nearest(
            res.png_bytes,
            requested_width,
            requested_height,
        )

        png_path = out_dir / "result.png"
        png_path.write_bytes(final_png_bytes)

        preview_path = out_dir / "preview.txt"
        preview_path.write_text(
            "sd_webui ok\n"
            f"job_id={jid}\n"
            f"type={job_type}\n"
            f"prompt={prompt}\n"
            f"negative_prompt={negative_prompt}\n"
            f"requested_size={requested_width}x{requested_height}\n"
            f"generation_size={generation_width}x{generation_height}\n"
            f"steps={steps}\n"
            f"cfg_scale={cfg_scale}\n"
            f"sampler={sampler_name}\n"
            f"seed={seed}\n",
            encoding="utf-8",
        )

        duration_ms = int((time.perf_counter() - started) * 1000)

        result_payload = build_result_v1(
            kind=str(job_type),
            engine="sd_webui",
            artifacts={
                "image": "out/result.png",
                "image_original": "out/result_512.png",
                "preview": "out/preview.txt",
            },
            meta={
                "prompt": prompt,
                "width": requested_width,
                "height": requested_height,
                "generation_width": generation_width,
                "generation_height": generation_height,
                "steps": steps,
                "duration_ms": duration_ms,
                "webui": res.info,
                "negative_prompt": negative_prompt,
                "cfg_scale": cfg_scale,
                "sampler_name": sampler_name,
                "seed": seed,
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