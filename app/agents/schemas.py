from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Pillar(BaseModel):
    name: str
    message: str
    proof_points: list[str] = Field(default_factory=list)


class ChannelPick(BaseModel):
    channel: str
    rationale: str
    expected_impact: Literal["high", "medium", "low"] = "medium"


class ResearchFinding(BaseModel):
    claim: str
    source_url: str | None = None
    source_title: str | None = None


class CampaignPlanDraft(BaseModel):
    positioning: str
    pillars: list[Pillar]
    audience_refinement: str
    channel_selection: list[ChannelPick]
    competitor_angle: str
    urgency_framing: str
    research_findings: list[ResearchFinding] = Field(default_factory=list)


class StepEvent(BaseModel):
    type: Literal[
        "run.started",
        "run.succeeded",
        "run.failed",
        "step.started",
        "step.succeeded",
        "step.failed",
        "log",
        "artifact",
    ]
    agent: str | None = None
    tool: str | None = None
    message: str | None = None
    data: dict[str, Any] | None = None
    step_id: str | None = None
