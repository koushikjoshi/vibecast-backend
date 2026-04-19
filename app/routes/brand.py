from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.deps import (
    CurrentWorkspace,
    get_current_user,
    get_current_workspace,
    require_owner_or_approver,
)
from app.models import BrandKit, BrandPreset, User

router = APIRouter(prefix="/w/{slug}/brand", tags=["brand"])


class BrandKitOut(BaseModel):
    id: UUID
    version: int
    preset: str
    tone: dict[str, Any]
    banned_phrases: list[str]
    required_disclaimers: list[str]
    competitor_policy: str
    pronunciation: list[dict[str, Any]]
    legal_footer: str
    positioning: str
    target_icp: str
    voice_samples: list[dict[str, Any]]
    created_at: datetime


def _serialize(kit: BrandKit) -> BrandKitOut:
    return BrandKitOut(
        id=kit.id,
        version=kit.version,
        preset=kit.preset,
        tone=json.loads(kit.tone_json or "{}"),
        banned_phrases=json.loads(kit.banned_phrases_json or "[]"),
        required_disclaimers=json.loads(kit.required_disclaimers_json or "[]"),
        competitor_policy=kit.competitor_policy,
        pronunciation=json.loads(kit.pronunciation_json or "[]"),
        legal_footer=kit.legal_footer,
        positioning=kit.positioning,
        target_icp=kit.target_icp,
        voice_samples=json.loads(kit.voice_samples_json or "[]"),
        created_at=kit.created_at,
    )


def _latest(session: Session, workspace_id: UUID) -> BrandKit | None:
    return session.exec(
        select(BrandKit)
        .where(BrandKit.workspace_id == workspace_id)
        .order_by(BrandKit.version.desc())
    ).first()


@router.get("", response_model=BrandKitOut)
def get_brand_kit(
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> BrandKitOut:
    kit = _latest(session, ws.id)
    if kit is None:
        raise HTTPException(status_code=404, detail="no brand kit for this workspace")
    return _serialize(kit)


@router.get("/versions", response_model=list[BrandKitOut])
def list_brand_versions(
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> list[BrandKitOut]:
    kits = session.exec(
        select(BrandKit)
        .where(BrandKit.workspace_id == ws.id)
        .order_by(BrandKit.version.desc())
    ).all()
    return [_serialize(k) for k in kits]


class BrandKitIn(BaseModel):
    preset: str | None = None
    tone: dict[str, Any] | None = None
    banned_phrases: list[str] | None = None
    required_disclaimers: list[str] | None = None
    competitor_policy: str | None = Field(default=None, pattern="^(blocked|name-only|comparative-ok)$")
    pronunciation: list[dict[str, Any]] | None = None
    legal_footer: str | None = None
    positioning: str | None = None
    target_icp: str | None = None
    voice_samples: list[dict[str, Any]] | None = None


@router.post("", response_model=BrandKitOut, status_code=201)
def create_brand_kit_version(
    body: BrandKitIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    ws: CurrentWorkspace = Depends(require_owner_or_approver),
) -> BrandKitOut:
    previous = _latest(session, ws.id)
    if previous is None:
        preset = body.preset or BrandPreset.professional.value
    else:
        preset = body.preset or previous.preset

    if preset not in {p.value for p in BrandPreset}:
        raise HTTPException(status_code=400, detail=f"invalid preset '{preset}'")

    next_version = 1 if previous is None else previous.version + 1

    def pick(new: Any, old: Any, default: Any) -> Any:
        if new is not None:
            return new
        return old if old is not None else default

    kit = BrandKit(
        workspace_id=ws.id,
        version=next_version,
        preset=preset,
        tone_json=json.dumps(pick(body.tone, json.loads(previous.tone_json) if previous else None, {})),
        banned_phrases_json=json.dumps(pick(body.banned_phrases, json.loads(previous.banned_phrases_json) if previous else None, [])),
        required_disclaimers_json=json.dumps(pick(body.required_disclaimers, json.loads(previous.required_disclaimers_json) if previous else None, [])),
        competitor_policy=pick(body.competitor_policy, previous.competitor_policy if previous else None, "name-only"),
        pronunciation_json=json.dumps(pick(body.pronunciation, json.loads(previous.pronunciation_json) if previous else None, [])),
        legal_footer=pick(body.legal_footer, previous.legal_footer if previous else None, ""),
        positioning=pick(body.positioning, previous.positioning if previous else None, ""),
        target_icp=pick(body.target_icp, previous.target_icp if previous else None, ""),
        voice_samples_json=json.dumps(pick(body.voice_samples, json.loads(previous.voice_samples_json) if previous else None, [])),
        created_by=user.id,
    )
    session.add(kit)
    session.commit()
    session.refresh(kit)
    return _serialize(kit)
