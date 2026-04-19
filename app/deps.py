"""Request-scoped dependencies.

Auth has been removed for the hackathon. Every request is treated as if it
came from a singleton `system@vibecast.local` user with owner-level access to
any workspace it touches. Workspaces are lazily created on first access so
the frontend can hit `/w/default` on a fresh deployment with no setup.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.db import get_session
from app.models import BrandKit, BrandPreset, Membership, Role, User, Workspace

logger = logging.getLogger("vibecast.deps")

SYSTEM_EMAIL = "system@vibecast.local"


def _get_or_create_system_user(session: Session) -> User:
    user = session.exec(select(User).where(User.email == SYSTEM_EMAIL)).first()
    if user is not None:
        return user
    user = User(email=SYSTEM_EMAIL, name="VibeCast")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _default_brand_defaults() -> dict:
    return {
        "tone": {"voice": "Clear, confident, evidence-first. No hype."},
        "banned_phrases": [
            "revolutionary",
            "game-changing",
            "industry-leading",
            "cutting-edge",
            "seamless",
        ],
        "required_disclaimers": [],
        "competitor_policy": "name-only",
        "pronunciation": [],
        "legal_footer": "",
    }


def _get_or_create_workspace(session: Session, slug: str, user_id: UUID) -> Workspace:
    ws = session.exec(select(Workspace).where(Workspace.slug == slug)).first()
    if ws is not None:
        return ws

    pretty_name = slug.replace("-", " ").title() if slug != "default" else "VibeCast"
    ws = Workspace(
        slug=slug,
        name=pretty_name,
        brand_preset=BrandPreset.professional.value,
        created_by=user_id,
    )
    session.add(ws)
    session.flush()

    defaults = _default_brand_defaults()
    session.add(
        BrandKit(
            workspace_id=ws.id,
            version=1,
            preset=BrandPreset.professional.value,
            tone_json=json.dumps(defaults["tone"]),
            banned_phrases_json=json.dumps(defaults["banned_phrases"]),
            required_disclaimers_json=json.dumps(defaults["required_disclaimers"]),
            competitor_policy=defaults["competitor_policy"],
            pronunciation_json=json.dumps(defaults["pronunciation"]),
            legal_footer=defaults["legal_footer"],
            positioning="",
            target_icp="",
            created_by=user_id,
        )
    )
    session.commit()
    session.refresh(ws)
    logger.info("auto-provisioned workspace slug=%s id=%s", ws.slug, ws.id)
    return ws


def _ensure_membership(session: Session, workspace_id: UUID, user_id: UUID) -> Membership:
    membership = session.exec(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user_id,
        )
    ).first()
    if membership is not None:
        return membership
    membership = Membership(
        workspace_id=workspace_id,
        user_id=user_id,
        role=Role.owner.value,
    )
    session.add(membership)
    session.commit()
    session.refresh(membership)
    return membership


def get_current_user(session: Session = Depends(get_session)) -> User:
    return _get_or_create_system_user(session)


class CurrentWorkspace:
    def __init__(self, workspace: Workspace, membership: Membership) -> None:
        self.workspace = workspace
        self.membership = membership

    @property
    def id(self) -> UUID:
        return self.workspace.id

    @property
    def role(self) -> str:
        return self.membership.role

    def require_role(self, *allowed: str) -> None:
        # Auth removed; every caller is effectively owner. Keep the method for
        # signature compatibility but make it a no-op.
        return None


def get_current_workspace(
    slug: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CurrentWorkspace:
    if not slug or len(slug) > 64:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid workspace slug")
    workspace = _get_or_create_workspace(session, slug, user.id)
    membership = _ensure_membership(session, workspace.id, user.id)
    return CurrentWorkspace(workspace=workspace, membership=membership)


def require_owner(ws: CurrentWorkspace = Depends(get_current_workspace)) -> CurrentWorkspace:
    return ws


def require_owner_or_approver(
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> CurrentWorkspace:
    return ws


def require_operator_or_above(
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> CurrentWorkspace:
    return ws
