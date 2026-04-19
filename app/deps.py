from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlmodel import Session, select

from app.auth import decode_session_jwt
from app.config import Settings, get_settings
from app.db import get_session
from app.models import Membership, Role, User, Workspace


def get_current_user(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    session_token: str | None = Cookie(default=None, alias="vibecast_session"),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    user_id = decode_session_jwt(session_token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return user


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
        if self.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{self.role}' lacks required access",
            )


def get_current_workspace(
    slug: str,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CurrentWorkspace:
    workspace = session.exec(select(Workspace).where(Workspace.slug == slug)).first()
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workspace not found")
    membership = session.exec(
        select(Membership).where(
            Membership.workspace_id == workspace.id,
            Membership.user_id == user.id,
        )
    ).first()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workspace not found")
    return CurrentWorkspace(workspace=workspace, membership=membership)


def require_owner(ws: CurrentWorkspace = Depends(get_current_workspace)) -> CurrentWorkspace:
    ws.require_role(Role.owner.value)
    return ws


def require_owner_or_approver(
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> CurrentWorkspace:
    ws.require_role(Role.owner.value, Role.approver.value)
    return ws


def require_operator_or_above(
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> CurrentWorkspace:
    ws.require_role(Role.owner.value, Role.approver.value, Role.operator.value)
    return ws
