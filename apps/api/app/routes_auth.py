import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User
from app.schemas import RegisterIn, LoginIn, MeOut
from app.auth_security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_NAME = "access_token"
COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"


def set_auth_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * 30,
    )


def clear_auth_cookie(resp: Response) -> None:
    resp.delete_cookie(key=COOKIE_NAME, path="/")


@router.post("/register", response_model=MeOut)
async def register(payload: RegisterIn, resp: Response, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    set_auth_cookie(resp, token)

    return MeOut(id=str(user.id), email=user.email)


@router.post("/login", response_model=MeOut)
async def login(payload: LoginIn, resp: Response, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    set_auth_cookie(resp, token)

    return MeOut(id=str(user.id), email=user.email)


@router.post("/logout")
async def logout(resp: Response):
    clear_auth_cookie(resp)
    return {"ok": True}


@router.get("/me", response_model=MeOut)
async def me(req: Request, db: AsyncSession = Depends(get_db)):
    token = req.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    stmt = select(User).where(User.id == user_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return MeOut(id=str(user.id), email=user.email)