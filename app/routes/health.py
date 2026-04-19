from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/health", tags=["health"])
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "env": settings.env,
        "service": "vibecast-backend",
        "version": "0.1.0",
    }
