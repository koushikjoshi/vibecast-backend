from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.agents.artifacts import REGISTRY, V1_TYPES
from app.agents.producer import create_producing_run, run_producing
from app.db import get_session
from app.deps import (
    CurrentWorkspace,
    get_current_user,
    get_current_workspace,
    require_operator_or_above,
    require_owner_or_approver,
)
from app.models import (
    Artifact,
    ArtifactApproval,
    ArtifactState,
    ApprovalDecision,
    CampaignPlan,
    MarketingProject,
    ProjectState,
    Run,
    RunPhase,
    RunStatus,
    User,
)

logger = logging.getLogger("vibecast.artifacts")


router = APIRouter(tags=["artifacts"])


class ArtifactSummary(BaseModel):
    id: UUID
    project_id: UUID
    studio: str
    type: str
    state: str
    title: str
    brand_verdict: str
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ArtifactOut(ArtifactSummary):
    content: dict[str, Any]
    brand_check: dict[str, Any]


class ProduceIn(BaseModel):
    types: list[str] | None = None


class ProduceKickoffOut(BaseModel):
    run_id: UUID
    project_id: UUID
    status: str
    types: list[str]


class ApproveDecisionIn(BaseModel):
    comment: str | None = None


def _load_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {"value": data}
    except json.JSONDecodeError:
        return {}


def _summary(art: Artifact) -> ArtifactSummary:
    guard = _load_json(art.brand_check_summary_json)
    verdict = guard.get("verdict", "pass") if isinstance(guard, dict) else "pass"
    return ArtifactSummary(
        id=art.id,
        project_id=art.project_id,
        studio=art.studio,
        type=art.type,
        state=art.state,
        title=art.title,
        brand_verdict=str(verdict),
        approved_by=art.approved_by,
        approved_at=art.approved_at,
        created_at=art.created_at,
        updated_at=art.updated_at,
    )


def _detail(art: Artifact) -> ArtifactOut:
    summary = _summary(art)
    return ArtifactOut(
        **summary.model_dump(),
        content=_load_json(art.content_json),
        brand_check=_load_json(art.brand_check_summary_json),
    )


# ---------------------------------------------------------------------------
# Kickoff producing run
# ---------------------------------------------------------------------------


@router.post(
    "/w/{slug}/projects/{project_id}/produce",
    response_model=ProduceKickoffOut,
    status_code=202,
)
def kickoff_producing(
    project_id: UUID,
    body: ProduceIn,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(require_operator_or_above),
) -> ProduceKickoffOut:
    project = session.get(MarketingProject, project_id)
    if project is None or project.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="project not found")

    latest_plan = session.exec(
        select(CampaignPlan)
        .where(CampaignPlan.project_id == project.id)
        .order_by(CampaignPlan.version.desc())
    ).first()
    if latest_plan is None or latest_plan.approved_at is None:
        raise HTTPException(
            status_code=400,
            detail="approve the campaign plan before producing artifacts",
        )

    existing = session.exec(
        select(Run).where(
            Run.project_id == project.id,
            Run.phase == RunPhase.producing.value,
            Run.status == RunStatus.running.value,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="producing run already in progress",
        )

    types = body.types if body.types else list(V1_TYPES)
    unknown = [t for t in types if t not in REGISTRY]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"unknown artifact types: {', '.join(unknown)}",
        )

    run = create_producing_run(session, project)
    background.add_task(run_producing, run.id, project.id, ws.id, types)
    return ProduceKickoffOut(
        run_id=run.id,
        project_id=project.id,
        status=run.status,
        types=types,
    )


@router.get(
    "/w/{slug}/projects/{project_id}/artifacts",
    response_model=list[ArtifactSummary],
)
def list_project_artifacts(
    project_id: UUID,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> list[ArtifactSummary]:
    project = session.get(MarketingProject, project_id)
    if project is None or project.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="project not found")
    rows = session.exec(
        select(Artifact)
        .where(Artifact.project_id == project.id)
        .order_by(Artifact.created_at)
    ).all()
    return [_summary(a) for a in rows]


@router.get("/w/{slug}/artifacts/{artifact_id}", response_model=ArtifactOut)
def get_artifact(
    artifact_id: UUID,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> ArtifactOut:
    art = session.get(Artifact, artifact_id)
    if art is None or art.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="artifact not found")
    return _detail(art)


@router.post("/w/{slug}/artifacts/{artifact_id}/approve", response_model=ArtifactOut)
def approve_artifact(
    artifact_id: UUID,
    body: ApproveDecisionIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    ws: CurrentWorkspace = Depends(require_owner_or_approver),
) -> ArtifactOut:
    art = session.get(Artifact, artifact_id)
    if art is None or art.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="artifact not found")
    if art.state not in {
        ArtifactState.awaiting_approval.value,
        ArtifactState.changes_requested.value,
    }:
        raise HTTPException(
            status_code=400,
            detail=f"cannot approve from state '{art.state}'",
        )
    art.state = ArtifactState.approved.value
    art.approved_by = user.id
    art.approved_at = datetime.now(tz=timezone.utc)
    art.updated_at = art.approved_at
    session.add(art)
    session.add(
        ArtifactApproval(
            artifact_id=art.id,
            actor_id=user.id,
            decision=ApprovalDecision.approved.value,
            comment=body.comment,
        )
    )

    project = session.get(MarketingProject, art.project_id)
    if project is not None:
        pending = session.exec(
            select(Artifact).where(
                Artifact.project_id == project.id,
                Artifact.state.in_(
                    [
                        ArtifactState.awaiting_approval.value,
                        ArtifactState.drafting.value,
                        ArtifactState.changes_requested.value,
                    ]
                ),
            )
        ).first()
        if pending is None:
            project.state = ProjectState.shipped.value
            session.add(project)

    session.commit()
    session.refresh(art)
    return _detail(art)


@router.post(
    "/w/{slug}/artifacts/{artifact_id}/request-changes",
    response_model=ArtifactOut,
)
def request_changes(
    artifact_id: UUID,
    body: ApproveDecisionIn,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    ws: CurrentWorkspace = Depends(require_owner_or_approver),
) -> ArtifactOut:
    art = session.get(Artifact, artifact_id)
    if art is None or art.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="artifact not found")
    art.state = ArtifactState.changes_requested.value
    art.updated_at = datetime.now(tz=timezone.utc)
    session.add(art)
    session.add(
        ArtifactApproval(
            artifact_id=art.id,
            actor_id=user.id,
            decision=ApprovalDecision.changes_requested.value,
            comment=body.comment,
        )
    )
    session.commit()
    session.refresh(art)
    return _detail(art)


@router.get(
    "/w/{slug}/projects/{project_id}/artifact-catalog",
    response_model=list[dict[str, str]],
)
def artifact_catalog(
    project_id: UUID,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> list[dict[str, str]]:
    project = session.get(MarketingProject, project_id)
    if project is None or project.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="project not found")
    return [
        {
            "type": g.spec.type,
            "studio": g.spec.studio,
            "title": g.spec.title,
            "description": g.spec.description,
        }
        for g in REGISTRY.values()
    ]
