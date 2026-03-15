import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Job
from app.schemas import JobCreateRequest, JobResponse
from app.celery_client import celery_app
from app.auth_deps import get_current_user_id

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

JOBS_ROOT = Path(os.getenv("JOBS_ROOT", "/data/jobs")).resolve()


@router.post("", response_model=JobResponse)
async def create_job(
    body: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    stmt = select(Job.job_id).where(
        Job.user_id == user_id,
        Job.status.in_(["queued", "running"]),
    ).limit(1)

    exists = (await db.execute(stmt)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Another job is already active")

    job = Job(
        job_id=uuid4(),
        user_id=user_id,
        type=body.type,
        status="queued",
        params=body.params,
        result=None,
        error=None,
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    celery_app.send_task("jobs.run", args=[str(job.job_id)])

    return JobResponse(
        job_id=job.job_id,
        user_id=job.user_id,
        type=job.type,
        status=job.status,
        params=job.params,
        result=job.result,
        error=job.error,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    stmt = select(Job).where(Job.job_id == job_id, Job.user_id == user_id)
    job = (await db.execute(stmt)).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=job.job_id,
        user_id=job.user_id,
        type=job.type,
        status=job.status,
        params=job.params,
        result=job.result,
        error=job.error,
    )


@router.get("/{job_id}/artifact/{rel_path:path}")
async def get_job_artifact(
    job_id: UUID,
    rel_path: str,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    # ownership check (и заодно существование job)
    stmt = select(Job.job_id).where(Job.job_id == job_id, Job.user_id == user_id)
    exists = (await db.execute(stmt)).scalar_one_or_none()
    if not exists:
        raise HTTPException(status_code=404, detail="Job not found")

    job_dir = (JOBS_ROOT / str(job_id)).resolve()
    file_path = (job_dir / rel_path).resolve()

    # path traversal protection: file_path должен быть внутри job_dir
    job_dir_str = str(job_dir)
    file_path_str = str(file_path)
    if not (file_path_str == job_dir_str or file_path_str.startswith(job_dir_str + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")

    return FileResponse(path=file_path_str)


@router.post("/{job_id}/mark_failed", response_model=JobResponse)
async def mark_failed(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    stmt = select(Job).where(Job.job_id == job_id, Job.user_id == user_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ["queued", "running"]:
        raise HTTPException(status_code=409, detail="Job is not active")

    DEV_ALLOW_MARK_FAILED = os.getenv("DEV_ALLOW_MARK_FAILED", "false").lower() == "true"
    if not DEV_ALLOW_MARK_FAILED:
        raise HTTPException(status_code=404, detail="Not found")

    job.status = "failed"
    job.error = "Marked failed manually (dev-time endpoint)"
    await db.commit()
    await db.refresh(job)

    return JobResponse(
        job_id=job.job_id,
        user_id=job.user_id,
        type=job.type,
        status=job.status,
        params=job.params,
        result=job.result,
        error=job.error,
    )