from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from app.agents.trace import subscribe
from app.db import get_session
from app.deps import CurrentWorkspace, get_current_workspace
from app.models import Run, Step

logger = logging.getLogger("vibecast.runs")

router = APIRouter(prefix="/w/{slug}/runs", tags=["runs"])


class StepOut(BaseModel):
    id: UUID
    agent: str
    tool: str | None = None
    status: str
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    input: dict | None = None
    output: dict | None = None
    started_at: datetime
    ended_at: datetime | None = None


class RunOut(BaseModel):
    id: UUID
    project_id: UUID
    phase: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    total_tokens_in: int
    total_tokens_out: int
    total_cost_usd: float
    error: str | None = None
    steps: list[StepOut]


def _decode(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"value": value}
    except json.JSONDecodeError:
        return None


@router.get("/{run_id}", response_model=RunOut)
def get_run(
    run_id: UUID,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> RunOut:
    run = session.get(Run, run_id)
    if run is None or run.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="run not found")

    steps = session.exec(
        select(Step).where(Step.run_id == run.id).order_by(Step.started_at)
    ).all()

    return RunOut(
        id=run.id,
        project_id=run.project_id,
        phase=run.phase,
        status=run.status,
        started_at=run.started_at,
        ended_at=run.ended_at,
        total_tokens_in=run.total_tokens_in,
        total_tokens_out=run.total_tokens_out,
        total_cost_usd=run.total_cost_usd,
        error=run.error,
        steps=[
            StepOut(
                id=s.id,
                agent=s.agent,
                tool=s.tool,
                status=s.status,
                model=s.model,
                tokens_in=s.tokens_in,
                tokens_out=s.tokens_out,
                cost_usd=s.cost_usd,
                duration_ms=s.duration_ms,
                input=_decode(s.input_json),
                output=_decode(s.output_json),
                started_at=s.started_at,
                ended_at=s.ended_at,
            )
            for s in steps
        ],
    )


@router.get("/{run_id}/events")
async def stream_run_events(
    run_id: UUID,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> EventSourceResponse:
    run = session.get(Run, run_id)
    if run is None or run.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_gen() -> AsyncIterator[dict]:
        async for evt in subscribe(run_id):
            yield {"event": evt.get("type", "message"), "data": json.dumps(evt)}

    return EventSourceResponse(event_gen())
