from __future__ import annotations

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


ResultKind = Literal["image", "sprites", "sound", "text"]


class ResultV2(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: Literal[2] = Field(default=2)
    kind: ResultKind

    engine: Optional[str] = None

    artifacts: Dict[str, str] = Field(default_factory=dict)
    meta: Dict[str, Any] = Field(default_factory=dict)