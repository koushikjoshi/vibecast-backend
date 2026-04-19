from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("")
async def list_traces() -> list[dict]:
    return []


@router.get("/{run_id}")
async def get_trace(run_id: str) -> dict:
    raise HTTPException(status_code=404, detail="Not implemented yet")
