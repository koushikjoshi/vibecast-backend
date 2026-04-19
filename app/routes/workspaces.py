from __future__ import annotations

import json
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.deps import CurrentWorkspace, get_current_user, get_current_workspace
from app.models import (
    BrandKit,
    BrandPreset,
    Membership,
    Role,
    User,
    Workspace,
)

router = APIRouter(tags=["workspaces"])


_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def slugify(value: str) -> str:
    slug = value.lower().strip().replace(" ", "-")
    slug = _SLUG_RE.sub("", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "workspace"


def _preset_defaults(preset: str) -> dict:
    base = {
        "banned_phrases": ["revolutionary", "game-changing", "industry-leading", "cutting-edge", "seamless"],
        "required_disclaimers": [],
        "competitor_policy": "name-only",
        "pronunciation": [],
        "legal_footer": "",
    }
    tone = {
        BrandPreset.playful.value: {"voice": "Warm, witty, human. Short sentences. Occasional wry humor."},
        BrandPreset.professional.value: {"voice": "Clear, confident, measured. No hype. Evidence before claims."},
        BrandPreset.authoritative.value: {"voice": "Direct, opinionated, citation-dense. Reads like the category expert."},
        BrandPreset.technical.value: {"voice": "Precise, jargon-aware, specificity over marketing gloss."},
        BrandPreset.blend.value: {"voice": "Professional with flashes of personality. Warm but credible."},
    }.get(preset, {"voice": "Clear, credible, human."})

    return {**base, "tone": tone}


# ---------------------------------------------------------------------------
# Self / me
# ---------------------------------------------------------------------------


class MembershipOut(BaseModel):
    workspace_id: UUID
    workspace_slug: str
    workspace_name: str
    role: str


class MeOut(BaseModel):
    id: UUID
    email: str
    name: str | None
    memberships: list[MembershipOut]


@router.get("/me", response_model=MeOut)
def me(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> MeOut:
    rows = session.exec(
        select(Membership, Workspace).where(Membership.user_id == user.id).join(
            Workspace, Workspace.id == Membership.workspace_id
        )
    ).all()

    memberships = [
        MembershipOut(
            workspace_id=ws.id,
            workspace_slug=ws.slug,
            workspace_name=ws.name,
            role=m.role,
        )
        for (m, ws) in rows
    ]

    return MeOut(id=user.id, email=user.email, name=user.name, memberships=memberships)


# ---------------------------------------------------------------------------
# Create workspace
# ---------------------------------------------------------------------------


class CreateWorkspaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = None
    brand_preset: str = BrandPreset.professional.value


class WorkspaceOut(BaseModel):
    id: UUID
    slug: str
    name: str
    brand_preset: str
    role: str


@router.post("/workspaces", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    body: CreateWorkspaceIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> WorkspaceOut:
    preset = body.brand_preset
    if preset not in {p.value for p in BrandPreset}:
        raise HTTPException(status_code=400, detail=f"invalid brand_preset '{preset}'")

    slug_candidate = slugify(body.slug or body.name)
    existing = session.exec(select(Workspace).where(Workspace.slug == slug_candidate)).first()
    if existing is not None:
        suffix = 2
        while session.exec(select(Workspace).where(Workspace.slug == f"{slug_candidate}-{suffix}")).first():
            suffix += 1
        slug_candidate = f"{slug_candidate}-{suffix}"

    workspace = Workspace(
        slug=slug_candidate,
        name=body.name.strip(),
        brand_preset=preset,
        created_by=user.id,
    )
    session.add(workspace)
    session.flush()

    membership = Membership(
        workspace_id=workspace.id,
        user_id=user.id,
        role=Role.owner.value,
    )
    session.add(membership)

    defaults = _preset_defaults(preset)
    brand_kit = BrandKit(
        workspace_id=workspace.id,
        version=1,
        preset=preset,
        tone_json=json.dumps(defaults["tone"]),
        banned_phrases_json=json.dumps(defaults["banned_phrases"]),
        required_disclaimers_json=json.dumps(defaults["required_disclaimers"]),
        competitor_policy=defaults["competitor_policy"],
        pronunciation_json=json.dumps(defaults["pronunciation"]),
        legal_footer=defaults["legal_footer"],
        positioning="",
        target_icp="",
        created_by=user.id,
    )
    session.add(brand_kit)
    session.commit()
    session.refresh(workspace)

    return WorkspaceOut(
        id=workspace.id,
        slug=workspace.slug,
        name=workspace.name,
        brand_preset=workspace.brand_preset,
        role=Role.owner.value,
    )


@router.get("/w/{slug}", response_model=WorkspaceOut)
def get_workspace(
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> WorkspaceOut:
    return WorkspaceOut(
        id=ws.workspace.id,
        slug=ws.workspace.slug,
        name=ws.workspace.name,
        brand_preset=ws.workspace.brand_preset,
        role=ws.membership.role,
    )
