from __future__ import annotations

from app.agents.artifacts.base import ArtifactGenerator
from app.agents.artifacts.content import (
    BlogGenerator,
    PressReleaseGenerator,
    ReleaseNotesGenerator,
)
from app.agents.artifacts.lifecycle import (
    BattleCardGenerator,
    CustomerEmailGenerator,
    ProspectEmailGenerator,
)
from app.agents.artifacts.podcast import PodcastEpisodeGenerator
from app.agents.artifacts.social import (
    HnShowGenerator,
    LinkedInCompanyGenerator,
    LinkedInFounderGenerator,
    ProductHuntGenerator,
    XThreadGenerator,
)

REGISTRY: dict[str, ArtifactGenerator] = {}


def _register(generator: ArtifactGenerator) -> None:
    REGISTRY[generator.spec.type] = generator


_GENERATORS: list[ArtifactGenerator] = [
    BlogGenerator(),
    PressReleaseGenerator(),
    ReleaseNotesGenerator(),
    XThreadGenerator(),
    LinkedInCompanyGenerator(),
    LinkedInFounderGenerator(),
    HnShowGenerator(),
    ProductHuntGenerator(),
    CustomerEmailGenerator(),
    ProspectEmailGenerator(),
    BattleCardGenerator(),
    PodcastEpisodeGenerator(),
]

for _g in _GENERATORS:
    _register(_g)


V1_TYPES: list[str] = [g.spec.type for g in _GENERATORS]
