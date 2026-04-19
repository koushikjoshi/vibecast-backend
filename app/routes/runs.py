from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

router = APIRouter()


class CreateRunRequest(BaseModel):
    topic: str
    format: str | None = None
    length: str | None = None
    cast: list[str] | None = None
    visibility: str = "public"


@router.post("")
async def create_run(_: CreateRunRequest) -> dict:
    raise HTTPException(status_code=501, detail="Run orchestration not wired up yet")


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    raise HTTPException(status_code=501, detail="SSE stream not wired up yet")
