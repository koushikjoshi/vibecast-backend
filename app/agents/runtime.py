from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.agents.executor_mock import PlanningInput, run_planning_mock
from app.agents.schemas import CampaignPlanDraft, StepEvent
from app.agents.trace import StepTracker, publish
from app.config import get_settings
from app.db import get_engine
from app.models import (
    BrandKit,
    CampaignPlan,
    Competitor,
    MarketingProject,
    ProjectSource,
    ProjectState,
    Run,
    RunPhase,
    RunStatus,
    UsageLedger,
)

logger = logging.getLogger("vibecast.agents.runtime")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_inputs(session: Session, project_id: UUID) -> PlanningInput | None:
    project = session.get(MarketingProject, project_id)
    if project is None:
        return None

    sources = session.exec(
        select(ProjectSource)
        .where(ProjectSource.project_id == project.id)
        .order_by(ProjectSource.created_at)
    ).all()

    brand_kit = session.exec(
        select(BrandKit)
        .where(BrandKit.workspace_id == project.workspace_id)
        .order_by(BrandKit.version.desc())
    ).first()

    if brand_kit is None:
        raise RuntimeError("workspace is missing a brand kit")

    competitors = session.exec(
        select(Competitor).where(Competitor.workspace_id == project.workspace_id)
    ).all()

    return PlanningInput(
        project=project,
        sources=sources,
        brand_kit=brand_kit,
        competitors=competitors,
    )


def _persist_plan(
    session: Session, project_id: UUID, plan: CampaignPlanDraft
) -> CampaignPlan:
    latest = session.exec(
        select(CampaignPlan)
        .where(CampaignPlan.project_id == project_id)
        .order_by(CampaignPlan.version.desc())
    ).first()
    version = (latest.version + 1) if latest else 1

    row = CampaignPlan(
        project_id=project_id,
        version=version,
        positioning=plan.positioning,
        pillars_json=json.dumps([p.model_dump() for p in plan.pillars]),
        audience_refinement=plan.audience_refinement,
        channel_selection_json=json.dumps(
            [c.model_dump() for c in plan.channel_selection]
        ),
        competitor_angle=plan.competitor_angle,
        urgency_framing=plan.urgency_framing,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def _select_executor():
    settings = get_settings()
    if settings.disable_live_runs:
        return run_planning_mock, "mock"
    if not os.getenv("ANTHROPIC_API_KEY") and not settings.anthropic_api_key:
        return run_planning_mock, "mock"
    try:
        from app.agents.executor_anthropic import run_planning_anthropic
        return run_planning_anthropic, "anthropic"
    except Exception as exc:  # noqa: BLE001
        logger.warning("anthropic executor unavailable (%s); falling back to mock", exc)
        return run_planning_mock, "mock"


async def run_planning(run_id: UUID, project_id: UUID, workspace_id: UUID) -> None:
    """Background task: drives a planning run end-to-end.

    Opens its OWN session (so the caller's request-scoped session can return
    immediately) and emits SSE events via the trace bus as it progresses.
    """
    engine = get_engine()
    executor, label = _select_executor()

    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run is None:
            logger.error("run %s not found", run_id)
            return

        tracker = StepTracker(session=session, run_id=run_id)
        publish(
            run_id,
            StepEvent(
                type="run.started",
                agent="cmo",
                message=f"Planning run started (executor: {label}).",
            ),
        )

        try:
            inputs = _load_inputs(session, project_id)
            if inputs is None:
                raise RuntimeError("project not found")

            project = inputs.project
            project.state = ProjectState.planning.value
            session.add(project)
            session.commit()

            plan = await executor(tracker, inputs)
            saved = _persist_plan(session, project_id, plan)

            project.state = ProjectState.plan_ready.value
            session.add(project)

            total_tokens_in = 0
            total_tokens_out = 0
            total_cost = 0.0
            for step in run_steps(session, run_id):
                if step.tokens_in:
                    total_tokens_in += step.tokens_in
                if step.tokens_out:
                    total_tokens_out += step.tokens_out
                if step.cost_usd:
                    total_cost += step.cost_usd

            run.status = RunStatus.succeeded.value
            run.ended_at = _now()
            run.total_tokens_in = total_tokens_in
            run.total_tokens_out = total_tokens_out
            run.total_cost_usd = round(total_cost, 4)
            session.add(run)

            session.add(
                UsageLedger(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    project_id=project_id,
                    tokens_in=total_tokens_in,
                    tokens_out=total_tokens_out,
                    cost_usd=round(total_cost, 4),
                )
            )
            session.commit()

            publish(
                run_id,
                StepEvent(
                    type="run.succeeded",
                    agent="cmo",
                    message=f"Plan v{saved.version} ready.",
                    data={
                        "campaign_plan_id": str(saved.id),
                        "version": saved.version,
                        "tokens_in": total_tokens_in,
                        "tokens_out": total_tokens_out,
                        "cost_usd": round(total_cost, 4),
                    },
                ),
            )
        except asyncio.CancelledError:
            run.status = RunStatus.failed.value
            run.ended_at = _now()
            run.error = "cancelled"
            session.add(run)
            session.commit()
            publish(
                run_id,
                StepEvent(type="run.failed", agent="cmo", message="Run cancelled."),
            )
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("planning run %s failed", run_id)
            run.status = RunStatus.failed.value
            run.ended_at = _now()
            run.error = str(exc)
            session.add(run)

            project = session.get(MarketingProject, project_id)
            if project is not None:
                project.state = ProjectState.intake.value
                session.add(project)

            session.commit()
            publish(
                run_id,
                StepEvent(
                    type="run.failed",
                    agent="cmo",
                    message=f"Run failed: {exc}",
                ),
            )


def run_steps(session: Session, run_id: UUID):
    from app.models import Step
    return session.exec(
        select(Step).where(Step.run_id == run_id).order_by(Step.started_at)
    ).all()


def create_run(session: Session, project: MarketingProject) -> Run:
    run = Run(
        workspace_id=project.workspace_id,
        project_id=project.id,
        phase=RunPhase.planning.value,
        status=RunStatus.running.value,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
