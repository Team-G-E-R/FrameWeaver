from __future__ import annotations

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


ResultKind = Literal["icon", "sprites", "sound", "text"]


class ResultV1(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: Literal[1] = Field(default=1)
    kind: ResultKind

    engine: Optional[str] = None

    artifacts: Dict[str, str] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)


def build_result_v1(
    *,
    kind: ResultKind,
    artifacts: Optional[Dict[str, str]] = None,
    meta: Optional[Dict[str, Any]] = None,
    engine: Optional[str] = None,
) -> Dict[str, Any]:
    r = ResultV1(
        kind=kind,
        engine=engine,
        artifacts=artifacts or {},
        meta=meta or {},
    )
    return r.model_dump()