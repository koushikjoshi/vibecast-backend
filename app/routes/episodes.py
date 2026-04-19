from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("")
async def list_episodes() -> list[dict]:
    return []


@router.get("/{episode_id}")
async def get_episode(episode_id: str) -> dict:
    raise HTTPException(status_code=404, detail="Not implemented yet")
