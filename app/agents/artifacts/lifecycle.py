from __future__ import annotations

from app.agents.artifacts._helpers import (
    brand_positioning,
    first_n,
    launch_date,
    pillar_lines,
    target_competitor,
)
from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts.content import _Base
from app.models import ArtifactStudio, ArtifactType


class CustomerEmailGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.customer_email.value,
        studio=ArtifactStudio.lifecycle.value,
        title="Customer announcement email",
        description="Broadcast to existing customers on launch day.",
    )
    anthropic_max_tokens = 1400
    anthropic_schema = (
        "{\n"
        '  "from_name": string (sender display name),\n'
        '  "subject": string (40-70 chars),\n'
        '  "preview_text": string (80-120 chars, email preview text),\n'
        '  "body_md": string (markdown body, 600-1200 chars),\n'
        '  "cta": {"label": string, "href": string}\n'
        "}"
    )
    anthropic_instructions = (
        "Warm, direct email to existing customers. Lead with what's new, "
        "what that means for them, and what (if anything) they have to do. "
        "Markdown body should use headings and short bullet lists. No hype "
        "superlatives. Sign off in the voice of the founding team."
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
                "Hi there,\n\n"
                f"Today we're shipping **{project.name}** to all workspaces \u2014 "
                "no upgrade required.\n\n"
                "**What's new:**\n\n"
                + "\n".join(
                    f"- {p}"
                    for p in (
                        pillars
                        or [
                            "Agentic marketing pipeline with 12 default artifacts",
                            "Brand Guardian enforcement",
                            "Live trace for every run",
                        ]
                    )
                )
                + "\n\nThe docs have migrated to the new layout \u2014 no action needed, "
                "but you'll see fresher examples.\n\nThanks for building with us.\n\n"
                f"\u2014 The {project.name} team"
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
    anthropic_max_tokens = 1100
    anthropic_schema = (
        "{\n"
        '  "from_name": string,\n'
        '  "subject": string (30-55 chars, low-key),\n'
        '  "preview_text": string (60-100 chars),\n'
        '  "body_md": string (markdown, 400-700 chars, includes {{first_name}} and at most one merge tag),\n'
        '  "cta": {"label": string, "href": string}\n'
        "}"
    )
    anthropic_instructions = (
        "Cold-nurture email to a prospect who has engaged before. Voice is "
        "a real sales/founder person, not a marketer. Short paragraphs. "
        "One merge tag maximum (e.g. {{first_name}}). No buzzwords. End "
        "with an ask that's low friction (e.g. 20-min chat, Loom)."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        return {
            "from_name": "Koushik at VibeCast",
            "subject": f"{project.name} is live \u2014 one brief, 12 artifacts",
            "preview_text": "A full marketing team on demand.",
            "body_md": (
                "Hi {{first_name}},\n\n"
                f"When we last spoke you mentioned {{pain_point}}. "
                f"Today we launched {project.name} \u2014 a multi-agent marketing team "
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
    anthropic_max_tokens = 1800
    anthropic_schema = (
        "{\n"
        '  "vs": string (competitor name),\n'
        '  "one_liner": string (our differentiator, <= 160 chars),\n'
        '  "when_we_win": array of 3-5 strings,\n'
        '  "when_we_lose": array of 2-4 strings (be honest),\n'
        '  "objection_handling": array of 3-5 objects {"objection": string, "reframe": string},\n'
        '  "proof_points": array of 3-5 strings\n'
        "}"
    )
    anthropic_instructions = (
        "Battle card for an AE heading into a deal. Keep language concrete: "
        "every bullet should be something a rep can literally say. Be honest "
        "about when we lose \u2014 fake invincibility destroys trust. Respect the "
        "brand's competitor_policy when phrasing comparisons."
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
                "Enterprises with deep in-house agency relationships",
                "Teams that need native social publishing (on roadmap)",
            ],
            "objection_handling": [
                {
                    "objection": f"We already use {rival}.",
                    "reframe": (
                        "That's great \u2014 most customers use us alongside, not "
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
                "~35 min from brief \u2192 approval queue",
                "Immutable brand-kit versions",
            ],
        }
