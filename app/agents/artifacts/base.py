from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence
from uuid import UUID

from app.models import (
    BrandKit,
    CampaignPlan,
    Competitor,
    MarketingProject,
    ProjectSource,
)


@dataclass
class GenContext:
    project: MarketingProject
    brand_kit: BrandKit
    competitors: Sequence[Competitor]
    sources: Sequence[ProjectSource]
    plan: CampaignPlan
    # Optional streaming wiring. When set, generators publish live token
    # chunks into the run's SSE bus so the frontend can render the model
    # "typing" live.
    run_id: UUID | None = None
    step_id: UUID | None = None
    agent_label: str = field(default="")


@dataclass
class ArtifactSpec:
    type: str
    studio: str
    title: str
    description: str


class ArtifactGenerator(Protocol):
    spec: ArtifactSpec

    async def generate_mock(self, ctx: GenContext) -> dict: ...

    async def generate_anthropic(self, ctx: GenContext) -> dict: ...
