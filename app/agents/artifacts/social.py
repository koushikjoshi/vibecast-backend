from __future__ import annotations

from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts._helpers import (
    brand_positioning,
    first_n,
    launch_date,
    pillar_lines,
    plan_pillars,
    target_competitor,
)
from app.agents.artifacts.content import _Base
from app.models import ArtifactStudio, ArtifactType


class XThreadGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.x_thread.value,
        studio=ArtifactStudio.social.value,
        title="X launch thread",
        description="7–9 post thread for X (Twitter).",
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        pillars = plan_pillars(ctx)
        posts: list[str] = [
            f"Today we're shipping {project.name}.\n\n{positioning}",
            "Why now?\n\nMarketing teams are stuck between $20k/mo agencies and one overworked PMM. We built a third option: a multi-agent team that works on your brief.",
        ]
        for p in pillars[:3]:
            posts.append(
                f"{p.get('name', '')}\n\n{p.get('message', '')}"
            )
        posts.append(
            "How it works:\n\n"
            "1. Upload a launch brief\n"
            "2. A CMO agent dispatches 17 specialists\n"
            "3. Every artifact is brand-checked\n"
            "4. You approve. We ship."
        )
        posts.append("12 artifacts per project: blog, press, release notes, LinkedIn (2), X thread, HN, Product Hunt, emails (2), battle card, and a podcast episode.")
        posts.append(f"Start your first project → https://vibecast.ai ({launch_date(ctx)})")
        return {
            "posts": posts,
            "hashtags": ["#buildinpublic", "#marketing", "#ai"],
        }


class LinkedInCompanyGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.linkedin_company.value,
        studio=ArtifactStudio.social.value,
        title="LinkedIn — company post",
        description="LinkedIn post from the company page.",
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        pillars = first_n(pillar_lines(ctx), 3)
        body = (
            f"Today we're shipping {project.name}.\n\n"
            f"{positioning}\n\n"
            "What that means in practice:\n"
            + "\n".join(f"• {p}" for p in (pillars or [
                "One brief → a full launch kit.",
                "Brand-safe by default.",
                "Evidence-backed, GEO-structured content.",
            ]))
            + "\n\nRead the launch: https://vibecast.ai/launch"
        )
        return {
            "post": body,
            "cta": {"label": "Read the launch", "href": "https://vibecast.ai/launch"},
        }


class LinkedInFounderGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.linkedin_founder.value,
        studio=ArtifactStudio.social.value,
        title="LinkedIn — founder post",
        description="First-person launch post from the founder.",
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        body = (
            f"A year ago I was the first marketing hire at a B2B startup. "
            "I was doing blog, press, social, lifecycle, and podcast — alone. "
            "I missed half of them.\n\n"
            f"Today we're shipping {project.name}.\n\n"
            f"{positioning}\n\n"
            "This is the tool I wish I had when I was that one overwhelmed PMM. "
            "If that's you — give this a try.\n\nLink in comments."
        )
        return {"post": body}


class HnShowGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.hn_show.value,
        studio=ArtifactStudio.social.value,
        title="HN 'Show HN' submission",
        description="Show HN title + first-comment body.",
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        title = f"Show HN: {project.name} — {positioning}"
        first_comment = (
            f"Hi HN! Founder here.\n\n"
            f"{project.name} is a multi-agent marketing team for B2B startups. "
            "You upload a launch brief, we spin up a CMO + 17 specialist agents, "
            "and you get a full launch kit (blog, press, social, email, podcast) "
            "ready for review in ~35 minutes.\n\n"
            "Under the hood: Claude Agent SDK for orchestration + supervised "
            "subagents, Anthropic web_search for live competitive research, "
            "GPT-image-1 for visuals, ElevenLabs for podcast audio.\n\n"
            "Would love feedback on the 12-artifact default and whether the "
            "Brand Guardian step feels strict enough. Happy to answer anything."
        )
        return {"title": title, "first_comment": first_comment}


class ProductHuntGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.product_hunt.value,
        studio=ArtifactStudio.social.value,
        title="Product Hunt kit",
        description="Tagline + first comment + 4 gallery briefs.",
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        return {
            "tagline": f"{project.name}: A full marketing team on demand.",
            "description": positioning,
            "first_comment": (
                f"Thanks for checking out {project.name}! We built this because "
                "every small B2B team we talked to had the same problem: one "
                "human marketer trying to do the work of five. This is a CMO + "
                "17 specialist agents that ship a full launch kit from a single "
                "brief. AMA!"
            ),
            "gallery_briefs": [
                {
                    "frame": 1,
                    "scene": "Hero shot of the VibeCast workspace with a project mid-run.",
                    "note": "Dark theme, show live trace panel on the right.",
                },
                {
                    "frame": 2,
                    "scene": "Campaign plan preview: positioning, 3 pillars, channel selection.",
                    "note": "Emphasize the 'approve plan' button.",
                },
                {
                    "frame": 3,
                    "scene": "Artifact grid with all 12 drafted deliverables.",
                    "note": "Use artifact-state color badges.",
                },
                {
                    "frame": 4,
                    "scene": "Podcast episode detail page: transcript + waveform + cover art.",
                    "note": "Show the RSS feed callout in the footer.",
                },
            ],
        }
