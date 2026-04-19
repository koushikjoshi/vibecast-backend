from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import UUID

from sqlmodel import Session

from app.agents.schemas import StepEvent
from app.models import Step, StepStatus

logger = logging.getLogger("vibecast.agents.trace")

_MAX_QUEUE = 256
_buses: dict[UUID, list[asyncio.Queue]] = {}
_history: dict[UUID, list[dict]] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def publish(run_id: UUID, event: StepEvent | dict) -> None:
    payload = event.model_dump(mode="json") if isinstance(event, StepEvent) else event
    _history.setdefault(run_id, []).append(payload)
    for q in list(_buses.get(run_id, [])):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("trace bus full for run %s, dropping event", run_id)


async def subscribe(run_id: UUID) -> AsyncIterator[dict]:
    queue: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUE)
    _buses.setdefault(run_id, []).append(queue)

    for evt in _history.get(run_id, []):
        await queue.put(evt)

    try:
        while True:
            try:
                evt = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                yield {"type": "heartbeat", "ts": _now().isoformat()}
                continue
            yield evt
            if evt.get("type") in {"run.succeeded", "run.failed"}:
                await asyncio.sleep(0.2)
                break
    finally:
        with suppress(ValueError):
            _buses[run_id].remove(queue)
        if not _buses.get(run_id):
            _buses.pop(run_id, None)


def drop_history(run_id: UUID) -> None:
    _history.pop(run_id, None)
    _buses.pop(run_id, None)


class StepTracker:
    def __init__(self, session: Session, run_id: UUID) -> None:
        self.session = session
        self.run_id = run_id

    def start(
        self,
        agent: str,
        *,
        tool: str | None = None,
        model: str | None = None,
        input_data: dict | None = None,
        parent_step_id: UUID | None = None,
    ) -> Step:
        step = Step(
            run_id=self.run_id,
            parent_step_id=parent_step_id,
            agent=agent,
            tool=tool,
            model=model,
            input_json=json.dumps(input_data) if input_data else None,
            status=StepStatus.running.value,
        )
        self.session.add(step)
        self.session.commit()
        self.session.refresh(step)
        publish(
            self.run_id,
            StepEvent(
                type="step.started",
                agent=agent,
                tool=tool,
                step_id=str(step.id),
                message=f"{agent}{f' · {tool}' if tool else ''} started",
            ),
        )
        return step

    def succeed(
        self,
        step: Step,
        *,
        output_data: dict | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost_usd: float | None = None,
    ) -> None:
        step.status = StepStatus.ok.value
        step.output_json = json.dumps(output_data) if output_data else None
        step.tokens_in = tokens_in
        step.tokens_out = tokens_out
        step.cost_usd = cost_usd
        step.ended_at = _now()
        if step.started_at:
            delta = step.ended_at - step.started_at
            step.duration_ms = int(delta.total_seconds() * 1000)
        self.session.add(step)
        self.session.commit()
        publish(
            self.run_id,
            StepEvent(
                type="step.succeeded",
                agent=step.agent,
                tool=step.tool,
                step_id=str(step.id),
                data={
                    "duration_ms": step.duration_ms,
                    "cost_usd": cost_usd,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                },
                message=f"{step.agent}{f' · {step.tool}' if step.tool else ''} ok",
            ),
        )

    def fail(self, step: Step, *, error: str) -> None:
        step.status = StepStatus.error.value
        step.output_json = json.dumps({"error": error})
        step.ended_at = _now()
        if step.started_at:
            delta = step.ended_at - step.started_at
            step.duration_ms = int(delta.total_seconds() * 1000)
        self.session.add(step)
        self.session.commit()
        publish(
            self.run_id,
            StepEvent(
                type="step.failed",
                agent=step.agent,
                tool=step.tool,
                step_id=str(step.id),
                message=error,
            ),
        )

    def log(self, agent: str, message: str, data: dict | None = None) -> None:
        publish(
            self.run_id,
            StepEvent(type="log", agent=agent, message=message, data=data),
        )
