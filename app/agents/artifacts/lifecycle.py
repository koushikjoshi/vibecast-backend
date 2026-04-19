from __future__ import annotations

from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts._helpers import (
    brand_positioning,
    first_n,
    launch_date,
    pillar_lines,
    target_competitor,
)
from app.agents.artifacts.content import _Base
from app.models import ArtifactStudio, ArtifactType


class CustomerEmailGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.customer_email.value,
        studio=ArtifactStudio.lifecycle.value,
        title="Customer announcement email",
        description="Broadcast to existing customers on launch day.",
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        pillars = first_n(pillar_lines(ctx), 3)
        return {
            "from_name": "The VibeCast team",
            "subject": f"Shipping today: {project.name}",
            "preview_text": positioning,
            "body_md": (
                f"Hi there,\n\n"
                f"Today we're shipping **{project.name}** to all workspaces — "
                "no upgrade required.\n\n"
                "**What's new:**\n\n"
                + "\n".join(f"- {p}" for p in (pillars or [
                    "Agentic marketing pipeline with 12 default artifacts",
                    "Brand Guardian enforcement",
                    "Live trace for every run",
                ]))
                + "\n\nThe docs have migrated to the new layout — no action needed, "
                "but you'll see fresher examples.\n\nThanks for building with us.\n\n"
                f"— The {project.name} team"
            ),
            "cta": {
                "label": "Explore the new workflow",
                "href": "https://vibecast.ai/app",
            },
        }


class ProspectEmailGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.prospect_email.value,
        studio=ArtifactStudio.lifecycle.value,
        title="Prospect nurture email",
        description="Cold-nurture email for active prospects.",
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        return {
            "from_name": "Koushik at VibeCast",
            "subject": f"{project.name} is live — one brief, 12 artifacts",
            "preview_text": "A full marketing team on demand.",
            "body_md": (
                f"Hi {{first_name}},\n\n"
                f"When we last spoke you mentioned {{pain_point}}. "
                f"Today we launched {project.name} — a multi-agent marketing team "
                "that takes a launch brief and produces a full campaign kit in "
                "under an hour.\n\n"
                f"{positioning}\n\n"
                "If that sounds relevant, I'd love to show you the demo live "
                "or share a 2-minute Loom. Either works.\n\n"
                "Koushik"
            ),
            "cta": {
                "label": "Book 20 minutes",
                "href": "https://vibecast.ai/book",
            },
        }


class BattleCardGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.battle_card.value,
        studio=ArtifactStudio.lifecycle.value,
        title="Battle card",
        description="Sales battle card focused on the primary competitor.",
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        rival = target_competitor(ctx) or "the incumbent"
        positioning = brand_positioning(ctx)
        return {
            "vs": rival,
            "one_liner": f"We win when {positioning.lower()}",
            "when_we_win": [
                f"Teams evaluating {rival} who want brand-safe output by default",
                "Solo PMMs / founder-led marketing",
                "B2B startups with a launch cadence of 1+ per quarter",
            ],
            "when_we_lose": [
                f"Enterprises with deep in-house agency relationships",
                f"Teams that need native social publishing (on roadmap)",
            ],
            "objection_handling": [
                {
                    "objection": f"We already use {rival}.",
                    "reframe": (
                        "That's great — most customers use us alongside, not "
                        "instead of. The difference: we produce the campaign kit; "
                        f"{rival} handles the ad spend."
                    ),
                },
                {
                    "objection": "Our brand voice is too specific for AI.",
                    "reframe": (
                        "That's exactly why every artifact passes a Brand Guardian "
                        "step that enforces your banned phrases and disclaimers "
                        "before it ever reaches you."
                    ),
                },
            ],
            "proof_points": [
                "12 artifacts per project by default",
                "~35 min from brief → approval queue",
                "Immutable brand-kit versions",
            ],
        }
