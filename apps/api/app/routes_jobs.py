import uuid

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Job
from app.schemas import JobCreateRequest, JobResponse

from app.celery_client import celery_app

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _get_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    try:
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-Id header")


@router.post("", response_model=JobResponse)
async def create_job(
    body: JobCreateRequest,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = _get_user_id(x_user_id)

    stmt = select(Job.job_id).where(
        Job.user_id == user_id,
        Job.status.in_(["queued", "running"]),
    ).limit(1)

    exists = (await db.execute(stmt)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail="Another job is already active")

    job = Job(
        job_id=uuid.uuid4(),
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
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = _get_user_id(x_user_id)

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

@router.post("/{job_id}/mark_failed", response_model=JobResponse)
async def mark_failed(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    user_id = _get_user_id(x_user_id)

    stmt = select(Job).where(Job.job_id == job_id, Job.user_id == user_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ["queued", "running"]:
        raise HTTPException(status_code=409, detail="Job is not active")

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