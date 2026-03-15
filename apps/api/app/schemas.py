import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, EmailStr


JobType = Literal["sprites", "sound", "text", "icon"]
JobStatus = Literal["queued", "running", "succeeded", "failed"]


class JobCreateRequest(BaseModel):
    type: JobType
    params: dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: uuid.UUID
    user_id: uuid.UUID
    type: JobType
    status: JobStatus
    params: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class MeOut(BaseModel):
    id: str
    email: EmailStr