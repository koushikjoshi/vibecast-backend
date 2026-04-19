from __future__ import annotations

import json
import logging
import os
import random
from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.agents import brand_guard
from app.agents.artifacts import REGISTRY, GenContext
from app.agents.schemas import StepEvent
from app.agents.trace import StepTracker, publish
from app.config import get_settings
from app.db import get_engine
from app.models import (
    Artifact,
    ArtifactState,
    BrandCheckDecision,
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

logger = logging.getLogger("vibecast.agents.producer")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _select_mode() -> str:
    settings = get_settings()
    if settings.disable_live_runs:
        return "mock"
    if not os.getenv("ANTHROPIC_API_KEY") and not settings.anthropic_api_key:
        return "mock"
    return "anthropic"


async def _load_ctx(session: Session, project_id: UUID) -> GenContext | None:
    project = session.get(MarketingProject, project_id)
    if project is None:
        return None
    plan = session.exec(
        select(CampaignPlan)
        .where(CampaignPlan.project_id == project.id)
        .order_by(CampaignPlan.version.desc())
    ).first()
    if plan is None:
        raise RuntimeError("no approved campaign plan for this project")
    brand = session.exec(
        select(BrandKit)
        .where(BrandKit.workspace_id == project.workspace_id)
        .order_by(BrandKit.version.desc())
    ).first()
    if brand is None:
        raise RuntimeError("workspace is missing a brand kit")
    sources = session.exec(
        select(ProjectSource)
        .where(ProjectSource.project_id == project.id)
        .order_by(ProjectSource.created_at)
    ).all()
    competitors = session.exec(
        select(Competitor).where(Competitor.workspace_id == project.workspace_id)
    ).all()
    return GenContext(
        project=project,
        brand_kit=brand,
        competitors=competitors,
        sources=sources,
        plan=plan,
    )


def _titleize(payload: dict, fallback: str) -> str:
    for key in ("headline", "title", "summary"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:160]
    return fallback


async def run_producing(
    run_id: UUID,
    project_id: UUID,
    workspace_id: UUID,
    types: list[str],
) -> None:
    engine = get_engine()
    mode = _select_mode()

    with Session(engine) as session:
        run = session.get(Run, run_id)
        if run is None:
            logger.error("producing run %s not found", run_id)
            return
        tracker = StepTracker(session=session, run_id=run_id)
        publish(
            run_id,
            StepEvent(
                type="run.started",
                agent="cmo",
                message=f"Producing {len(types)} artifact(s) (executor: {mode}).",
            ),
        )
        try:
            ctx = await _load_ctx(session, project_id)
            if ctx is None:
                raise RuntimeError("project not found")

            project = ctx.project
            if project.state != ProjectState.producing.value:
                project.state = ProjectState.producing.value
                session.add(project)
                session.commit()

            created_artifacts: list[Artifact] = []
            for artifact_type in types:
                generator = REGISTRY.get(artifact_type)
                if generator is None:
                    tracker.log(
                        "cmo", f"skipping unknown artifact type '{artifact_type}'"
                    )
                    continue

                agent_name = f"{generator.spec.studio}:{generator.spec.type}"
                step = tracker.start(
                    agent_name,
                    tool="draft",
                    model="sonnet" if mode == "anthropic" else "mock",
                    input_data={"type": artifact_type},
                )
                try:
                    if mode == "anthropic":
                        payload = await generator.generate_anthropic(ctx)
                    else:
                        payload = await generator.generate_mock(ctx)
                except Exception as exc:  # noqa: BLE001
                    tracker.fail(step, error=str(exc))
                    continue

                tokens_in = random.randint(1400, 2600) if mode == "mock" else None
                tokens_out = random.randint(600, 1400) if mode == "mock" else None
                cost = round(0.012 + random.random() * 0.018, 4) if mode == "mock" else None
                tracker.succeed(
                    step,
                    output_data={"preview_keys": list(payload.keys())[:6]},
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost,
                )

                guard_step = tracker.start(
                    "brand-guardian",
                    tool="check",
                    model="mock",
                    input_data={"target_type": artifact_type},
                )
                check = brand_guard.check(payload, ctx.brand_kit)
                tracker.succeed(
                    guard_step,
                    output_data=check.to_summary(),
                    tokens_in=120,
                    tokens_out=60,
                    cost_usd=0.0004,
                )

                art = Artifact(
                    project_id=project.id,
                    workspace_id=project.workspace_id,
                    studio=generator.spec.studio,
                    type=generator.spec.type,
                    state=(
                        ArtifactState.failed.value
                        if not check.passed
                        else ArtifactState.awaiting_approval.value
                    ),
                    title=_titleize(payload, generator.spec.title),
                    content_json=json.dumps(payload),
                    brand_check_summary_json=json.dumps(check.to_summary()),
                )
                session.add(art)
                session.flush()

                for f in check.findings:
                    session.add(
                        BrandCheckDecision(
                            run_id=run_id,
                            step_id=guard_step.id,
                            artifact_id=art.id,
                            section_ref=f.section_ref,
                            verdict=f.verdict,
                            rule=f.rule,
                            note=f.note,
                            suggested_rewrite=f.suggested_rewrite,
                        )
                    )
                session.commit()
                session.refresh(art)
                created_artifacts.append(art)
                publish(
                    run_id,
                    StepEvent(
                        type="artifact",
                        agent=agent_name,
                        message=f"Drafted {generator.spec.title}",
                        data={
                            "artifact_id": str(art.id),
                            "type": art.type,
                            "state": art.state,
                            "brand_verdict": check.verdict,
                        },
                    ),
                )

            project.state = ProjectState.reviewing.value
            session.add(project)

            total_in = 0
            total_out = 0
            total_cost = 0.0
            from app.models import Step
            steps = session.exec(
                select(Step).where(Step.run_id == run_id)
            ).all()
            for s in steps:
                if s.tokens_in:
                    total_in += s.tokens_in
                if s.tokens_out:
                    total_out += s.tokens_out
                if s.cost_usd:
                    total_cost += s.cost_usd

            run.status = RunStatus.succeeded.value
            run.ended_at = _now()
            run.total_tokens_in = total_in
            run.total_tokens_out = total_out
            run.total_cost_usd = round(total_cost, 4)
            session.add(run)
            session.add(
                UsageLedger(
                    workspace_id=workspace_id,
                    run_id=run_id,
                    project_id=project_id,
                    tokens_in=total_in,
                    tokens_out=total_out,
                    cost_usd=round(total_cost, 4),
                )
            )
            session.commit()
            publish(
                run_id,
                StepEvent(
                    type="run.succeeded",
                    agent="cmo",
                    message=f"Drafted {len(created_artifacts)} artifact(s).",
                    data={
                        "artifact_count": len(created_artifacts),
                        "cost_usd": round(total_cost, 4),
                    },
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("producing run %s failed", run_id)
            run.status = RunStatus.failed.value
            run.ended_at = _now()
            run.error = str(exc)
            session.add(run)
            session.commit()
            publish(
                run_id,
                StepEvent(
                    type="run.failed",
                    agent="cmo",
                    message=f"Run failed: {exc}",
                ),
            )


def create_producing_run(session: Session, project: MarketingProject) -> Run:
    run = Run(
        workspace_id=project.workspace_id,
        project_id=project.id,
        phase=RunPhase.producing.value,
        status=RunStatus.running.value,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run
