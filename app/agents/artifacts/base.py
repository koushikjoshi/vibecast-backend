from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

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
