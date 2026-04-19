from __future__ import annotations

from app.agents.artifacts._helpers import (
    brand_positioning,
    first_n,
    launch_date,
    pillar_lines,
    plan_pillars,
)
from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts.content import _Base
from app.models import ArtifactStudio, ArtifactType


class XThreadGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.x_thread.value,
        studio=ArtifactStudio.social.value,
        title="X launch thread",
        description="7\u20139 post thread for X (Twitter).",
    )
    anthropic_max_tokens = 1800
    anthropic_schema = (
        "{\n"
        '  "posts": array of 7-9 strings, each <= 280 characters including whitespace,\n'
        '  "hashtags": array of 2-4 strings starting with #\n'
        "}"
    )
    anthropic_instructions = (
        "Write an X (Twitter) launch thread of 7 to 9 posts. The first post "
        "must hook in under 200 chars. Subsequent posts can carry more "
        "detail but NEVER exceed 280 chars each. Use line breaks inside "
        "posts for readability. Keep the founder voice \u2014 first-person plural "
        "for the company, first-person singular for founder sentiment. End "
        "with a CTA post that includes a link placeholder."
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
            posts.append(f"{p.get('name', '')}\n\n{p.get('message', '')}")
        posts.append(
            "How it works:\n\n"
            "1. Upload a launch brief\n"
            "2. A CMO agent dispatches 17 specialists\n"
            "3. Every artifact is brand-checked\n"
            "4. You approve. We ship."
        )
        posts.append(
            "12 artifacts per project: blog, press, release notes, LinkedIn (2), X thread, HN, Product Hunt, emails (2), battle card, and a podcast episode."
        )
        posts.append(f"Start your first project \u2192 https://vibecast.ai ({launch_date(ctx)})")
        return {
            "posts": posts,
            "hashtags": ["#buildinpublic", "#marketing", "#ai"],
        }


class LinkedInCompanyGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.linkedin_company.value,
        studio=ArtifactStudio.social.value,
        title="LinkedIn \u2014 company post",
        description="LinkedIn post from the company page.",
    )
    anthropic_max_tokens = 900
    anthropic_schema = (
        "{\n"
        '  "post": string (1200-2000 chars, LinkedIn-formatted with line breaks and bullets),\n'
        '  "cta": {"label": string, "href": string}\n'
        "}"
    )
    anthropic_instructions = (
        "Write a LinkedIn company-page post. Structure: hook sentence, then a "
        "crisp statement of the launch, then a bullet list of 3 concrete "
        "outcomes, then a CTA line. Avoid emoji clutter (at most one). Use "
        "LinkedIn-native line-break rhythm (short paragraphs, blank lines "
        "between them)."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        pillars = first_n(pillar_lines(ctx), 3)
        body = (
            f"Today we're shipping {project.name}.\n\n"
            f"{positioning}\n\n"
            "What that means in practice:\n"
            + "\n".join(
                f"\u2022 {p}"
                for p in (
                    pillars
                    or [
                        "One brief \u2192 a full launch kit.",
                        "Brand-safe by default.",
                        "Evidence-backed, GEO-structured content.",
                    ]
                )
            )
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
        title="LinkedIn \u2014 founder post",
        description="First-person launch post from the founder.",
    )
    anthropic_max_tokens = 900
    anthropic_schema = '{\n  "post": string (800-1500 chars, first-person, LinkedIn-formatted)\n}'
    anthropic_instructions = (
        "Write a first-person LinkedIn post from the founder. Lead with a "
        "specific personal anecdote (keep it plausible, not grandiose). "
        "Transition to the launch and why it matters. End with a \u2018link in "
        "comments\u2019 line. No emojis, no hype. LinkedIn-native line rhythm."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        body = (
            "A year ago I was the first marketing hire at a B2B startup. "
            "I was doing blog, press, social, lifecycle, and podcast \u2014 alone. "
            "I missed half of them.\n\n"
            f"Today we're shipping {project.name}.\n\n"
            f"{positioning}\n\n"
            "This is the tool I wish I had when I was that one overwhelmed PMM. "
            "If that's you \u2014 give this a try.\n\nLink in comments."
        )
        return {"post": body}


class HnShowGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.hn_show.value,
        studio=ArtifactStudio.social.value,
        title="HN 'Show HN' submission",
        description="Show HN title + first-comment body.",
    )
    anthropic_max_tokens = 1100
    anthropic_schema = (
        "{\n"
        '  "title": string (Hacker News "Show HN:" title, 60-90 chars),\n'
        '  "first_comment": string (founder-style first comment, 600-1000 chars)\n'
        "}"
    )
    anthropic_instructions = (
        "HN audience is technical and skeptical. Title must start with "
        "'Show HN: '. First comment should introduce the founder, give an "
        "honest technical summary (what's under the hood), acknowledge "
        "known limitations, and invite feedback. No marketing adjectives."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        title = f"Show HN: {project.name} \u2014 {positioning}"
        first_comment = (
            "Hi HN! Founder here.\n\n"
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
    anthropic_max_tokens = 1400
    anthropic_schema = (
        "{\n"
        '  "tagline": string (<= 60 chars),\n'
        '  "description": string (260-300 chars, Product Hunt description),\n'
        '  "first_comment": string (founder intro comment, 500-800 chars),\n'
        '  "gallery_briefs": array of exactly 4 objects {"frame": int, "scene": string, "note": string}\n'
        "}"
    )
    anthropic_instructions = (
        "Produce a Product Hunt launch kit. Tagline must be punchy and under "
        "60 characters. Description must fit PH's ~260-char limit. First "
        "comment should read like a real founder intro (warm, honest, brief). "
        "Gallery briefs are prompts for image generation \u2014 describe what each "
        "frame shows, not marketing copy."
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
