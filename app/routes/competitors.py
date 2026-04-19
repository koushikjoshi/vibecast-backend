from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, HttpUrl
from sqlmodel import Session, select

from app.db import get_session
from app.deps import (
    CurrentWorkspace,
    get_current_workspace,
    require_operator_or_above,
)
from app.models import Competitor

router = APIRouter(prefix="/w/{slug}/competitors", tags=["competitors"])


class CompetitorOut(BaseModel):
    id: UUID
    name: str
    website_url: str
    pricing_url: str | None = None
    changelog_url: str | None = None
    positioning_cached: str | None = None
    research: dict[str, Any] | None = None
    last_fetched_at: datetime | None = None
    created_at: datetime


def _serialize(c: Competitor) -> CompetitorOut:
    research = None
    if c.research_json_cached:
        try:
            research = json.loads(c.research_json_cached)
        except json.JSONDecodeError:
            research = None
    return CompetitorOut(
        id=c.id,
        name=c.name,
        website_url=c.website_url,
        pricing_url=c.pricing_url,
        changelog_url=c.changelog_url,
        positioning_cached=c.positioning_cached,
        research=research,
        last_fetched_at=c.last_fetched_at,
        created_at=c.created_at,
    )


@router.get("", response_model=list[CompetitorOut])
def list_competitors(
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> list[CompetitorOut]:
    rows = session.exec(
        select(Competitor)
        .where(Competitor.workspace_id == ws.id)
        .order_by(Competitor.created_at)
    ).all()
    return [_serialize(c) for c in rows]


class CompetitorIn(BaseModel):
    name: str
    website_url: HttpUrl
    pricing_url: HttpUrl | None = None
    changelog_url: HttpUrl | None = None


@router.post("", response_model=CompetitorOut, status_code=201)
def create_competitor(
    body: CompetitorIn,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(require_operator_or_above),
) -> CompetitorOut:
    c = Competitor(
        workspace_id=ws.id,
        name=body.name.strip(),
        website_url=str(body.website_url),
        pricing_url=str(body.pricing_url) if body.pricing_url else None,
        changelog_url=str(body.changelog_url) if body.changelog_url else None,
    )
    session.add(c)
    session.commit()
    session.refresh(c)
    return _serialize(c)


@router.get("/{competitor_id}", response_model=CompetitorOut)
def get_competitor(
    competitor_id: UUID,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> CompetitorOut:
    c = session.get(Competitor, competitor_id)
    if c is None or c.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="competitor not found")
    return _serialize(c)


@router.delete("/{competitor_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_competitor(
    competitor_id: UUID,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(require_operator_or_above),
) -> Response:
    c = session.get(Competitor, competitor_id)
    if c is None or c.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="competitor not found")
    session.delete(c)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
