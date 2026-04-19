"""Stub auth router.

Auth was removed for the hackathon. These endpoints remain only to keep old
frontend builds from 404'ing; they always succeed and never issue or read a
session cookie.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/magic-link", status_code=status.HTTP_204_NO_CONTENT)
def request_magic_link() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/magic-link/consume")
def consume_magic_link_api() -> dict:
    return {"id": "00000000-0000-0000-0000-000000000000", "email": "system@vibecast.local", "name": "VibeCast"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
