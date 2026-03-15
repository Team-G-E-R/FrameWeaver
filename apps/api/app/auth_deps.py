import os
import uuid
from fastapi import HTTPException, Request
from .auth_security import decode_access_token

COOKIE_NAME = "access_token"
ALLOW_X_USER_ID = os.getenv("AUTH_DEV_ALLOW_X_USER_ID", "false").lower() == "true"

def _to_uuid(val: str | None) -> uuid.UUID | None:
    if not val:
        return None
    try:
        return uuid.UUID(val)
    except ValueError:
        return None

def get_current_user_id(req: Request) -> uuid.UUID:
    token = req.cookies.get(COOKIE_NAME)
    if token:
        sub = decode_access_token(token)
        user_uuid = _to_uuid(sub)
        if user_uuid:
            return user_uuid

    if ALLOW_X_USER_ID:
        user_uuid = _to_uuid(req.headers.get("X-User-Id"))
        if user_uuid:
            return user_uuid

    raise HTTPException(status_code=401, detail="Not authenticated")