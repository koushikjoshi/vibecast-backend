from __future__ import annotations

import logging
from typing import ClassVar

from app.agents.artifacts._anthropic import generate_via_claude
from app.agents.artifacts._helpers import (
    brand_positioning,
    brand_voice,
    first_n,
    launch_date,
    pillar_lines,
    plan_pillars,
    target_competitor,
)
from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.models import ArtifactStudio, ArtifactType

logger = logging.getLogger("vibecast.artifacts.content")


class _Base:
    spec: ArtifactSpec
    anthropic_schema: ClassVar[str] = ""
    anthropic_instructions: ClassVar[str] = ""
    anthropic_max_tokens: ClassVar[int] = 2500

    async def generate_anthropic(self, ctx: GenContext) -> dict:
        if not self.anthropic_schema:
            logger.info(
                "artifact %s has no anthropic_schema; using mock output",
                self.spec.type,
            )
            return await self.generate_mock(ctx)
        try:
            return await generate_via_claude(
                ctx,
                artifact_type=self.spec.type,
                studio=self.spec.studio,
                title=self.spec.title,
                anthropic_schema=self.anthropic_schema,
                anthropic_instructions=self.anthropic_instructions,
                max_tokens=self.anthropic_max_tokens,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "claude generation failed for %s (%s); falling back to mock",
                self.spec.type,
                exc,
            )
            return await self.generate_mock(ctx)


class BlogGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.blog.value,
        studio=ArtifactStudio.content.value,
        title="Launch blog post (GEO-optimized)",
        description="Long-form launch blog structured for AI retrieval (GEO) and social sharing.",
    )
    anthropic_max_tokens = 3200
    anthropic_schema = (
        "{\n"
        '  "headline": string (SEO title, 60-80 chars),\n'
        '  "subhead": string (dek, 120-180 chars),\n'
        '  "tldr": array of 3-5 string bullets for AI-retrieval summary,\n'
        '  "sections": array of {"heading": string, "body": string} with 5-7 items,\n'
        '  "faq": array of {"q": string, "a": string} with 3-5 items,\n'
        '  "cta": {"label": string, "href": string},\n'
        '  "geo_schema": {"@context": "https://schema.org", "@type": "Article", "headline": string, "description": string, "datePublished": string ISO date, "about": string},\n'
        '  "voice_note": string (one line summarizing tone choices made)\n'
        "}"
    )
    anthropic_instructions = (
        "Write a long-form launch blog post optimized for Generative Engine "
        "Optimization (GEO) — which means: lead with a crisp TL;DR, use "
        "scannable section headings that match likely AI retrieval queries, "
        "and include a FAQ section with literal question phrasings. Each "
        "section body should be 80-160 words, concrete, and cite evidence "
        "from the source material instead of abstract claims. Avoid hype "
        "language. Avoid filler transitions. The post should read like a "
        "credible launch announcement from a senior PMM, not a generic AI "
        "output."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        pillars = plan_pillars(ctx)
        project = ctx.project
        positioning = brand_positioning(ctx)
        voice = brand_voice(ctx)
        tagline = positioning.strip().rstrip(".")

        headline = f"Introducing {project.name}: {tagline}"
        subhead = (
            f"Ship your next launch in hours with a full marketing team of AI agents, "
            f"brand-checked and ready to ship."
        )
        tldr = [
            f"{project.name} is generally available today.",
            positioning,
            f"Launch date: {launch_date(ctx)}.",
        ]
        sections: list[dict] = [
            {
                "heading": "Why we built this",
                "body": (
                    f"B2B marketing teams are stuck between two bad options: hire an "
                    f"expensive agency, or ask one PMM to do five jobs. {project.name} is "
                    f"a third option — a fully agentic marketing team that ships on your "
                    f"brief, respects your brand, and costs a fraction of either."
                ),
            }
        ]
        for p in pillars:
            sections.append(
                {
                    "heading": p.get("name", ""),
                    "body": p.get("message", ""),
                }
            )
        sections.append(
            {
                "heading": "What's shipping today",
                "body": (
                    f"A launch brief, 12 artifacts per project, a podcast "
                    "episode, and a live trace of every agent decision. "
                    "Every artifact is brand-checked before it reaches "
                    "your approval queue."
                ),
            }
        )
        sections.append(
            {
                "heading": "How to get started",
                "body": (
                    "Create a workspace, define your brand kit, add your "
                    "competitors, then create your first Marketing Project. "
                    "Upload the launch doc and hit run."
                ),
            }
        )

        faq = [
            {
                "q": f"What is {project.name}?",
                "a": positioning,
            },
            {
                "q": "How is this different from ChatGPT?",
                "a": (
                    "ChatGPT is a single model you prompt. VibeCast is a supervised "
                    "multi-agent team (CMO + specialists) that follows your brand "
                    "kit, cites live web research, and ships a full launch kit you "
                    "can approve in one place."
                ),
            },
            {
                "q": "Which artifacts does it produce?",
                "a": (
                    "Blog, press release, release notes, LinkedIn + X + HN + "
                    "Product Hunt copy, customer + prospect email, battle card, "
                    "and a podcast episode with RSS feed."
                ),
            },
        ]

        cta = {
            "label": f"Start your first {project.name} project",
            "href": "https://vibecast.ai/signup",
        }

        geo_schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": headline,
            "description": subhead,
            "datePublished": launch_date(ctx),
            "about": positioning,
        }

        return {
            "headline": headline,
            "subhead": subhead,
            "tldr": tldr,
            "sections": sections,
            "faq": faq,
            "cta": cta,
            "geo_schema": geo_schema,
            "voice_note": voice,
        }


class PressReleaseGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.press_release.value,
        studio=ArtifactStudio.content.value,
        title="Press release",
        description="AP-style press release for launch day.",
    )
    anthropic_max_tokens = 1800
    anthropic_schema = (
        "{\n"
        '  "dateline": string (CITY, DATE format),\n'
        '  "headline": string (press-release style, 70-90 chars),\n'
        '  "body_paragraphs": array of 4-6 strings (300-500 chars each),\n'
        '  "quote": string (a realistic-sounding quote from a named founder or exec, <= 280 chars),\n'
        '  "boilerplate": string (2-3 sentence "About" block),\n'
        '  "contact": {"name": string, "email": string, "url": string},\n'
        '  "disclaimer": string (safe-harbor / forward-looking statement)\n'
        "}"
    )
    anthropic_instructions = (
        "Write in AP-style press release format. Lead paragraph must answer "
        "who/what/when/where/why. Body should include one quote from a "
        "realistically-named internal executive (invent the name but keep it "
        "plausible for the company). Avoid marketing hype — emulate the "
        "voice of a serious enterprise press release. End with boilerplate "
        "+ contact + safe-harbor disclaimer."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        positioning = brand_positioning(ctx)
        quote_pillars = first_n(plan_pillars(ctx), 1)
        pillar_quote_source = (
            quote_pillars[0].get("message", "")
            if quote_pillars
            else "We want to give every B2B team the marketing horsepower of a Series-B startup."
        )

        dateline = f"{launch_date(ctx).upper()}"
        headline = f"{project.name} launches: {positioning}"
        body = [
            f"{project.name} today announced the general availability of its "
            "agentic marketing platform, a supervised multi-agent system that "
            "replaces the first marketing hire for B2B startups.",
            f"Unlike single-model generative tools, {project.name} is built around "
            "a CMO-style orchestrator that dispatches specialist agents for "
            "research, positioning, content, social, lifecycle, and podcast "
            "production — each grounded in an immutable brand kit.",
            f"\u201c{pillar_quote_source}\u201d said the founding team. \u201cToday we're "
            "shipping a system that lets a solo PMM punch several weight "
            "classes above their headcount, without trading away brand safety.\u201d",
        ]
        boilerplate = (
            f"About {project.name}: "
            f"{positioning}. Founded in 2026. Based globally. Powered by the "
            "Claude Agent SDK and GPT-image generation."
        )
        contact = {
            "name": "Press desk",
            "email": "press@vibecast.ai",
            "url": "https://vibecast.ai/press",
        }

        return {
            "dateline": dateline,
            "headline": headline,
            "body_paragraphs": body,
            "quote": pillar_quote_source,
            "boilerplate": boilerplate,
            "contact": contact,
            "disclaimer": (
                ctx.brand_kit.legal_footer
                or "Forward-looking statements are predictions and subject to change."
            ),
        }


class ReleaseNotesGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.release_notes.value,
        studio=ArtifactStudio.content.value,
        title="Release notes entry",
        description="Changelog-style release notes for your product site.",
    )
    anthropic_max_tokens = 1200
    anthropic_schema = (
        "{\n"
        '  "version": string (semver or date),\n'
        '  "summary": string (one-line summary of the release),\n'
        '  "bullets": array of 4-8 strings, each prefixed with [New]/[Improved]/[Fixed],\n'
        '  "upgrade_notes": array of 1-3 strings,\n'
        '  "compatibility": string (one-line compatibility note)\n'
        "}"
    )
    anthropic_instructions = (
        "Produce a product-changelog entry in the style of a mature B2B SaaS "
        "(think Linear or Stripe). Bullets should be concrete and verb-first. "
        "Do not invent features that aren't in the source material."
    )

    async def generate_mock(self, ctx: GenContext) -> dict:
        project = ctx.project
        pillars = pillar_lines(ctx)
        summary = f"Shipping {project.name} — "
        summary += ctx.plan.positioning or "a new chapter for our platform."

        bullets = [
            f"[New] {p}" for p in pillars[:4]
        ] or [
            "[New] Agentic marketing pipeline now ships 12 artifacts per project.",
            "[Improved] Brand Guardian enforces banned phrases + required disclaimers.",
            "[Improved] Live SSE trace shows every agent decision in real time.",
        ]

        upgrade_notes = [
            "No action required — this release is automatic for all workspaces.",
            "New env vars documented in the admin console.",
        ]

        target = target_competitor(ctx)
        compat = (
            f"Importers now available for {target}." if target else "Importers unchanged."
        )

        return {
            "version": f"{launch_date(ctx)}",
            "summary": summary,
            "bullets": bullets,
            "upgrade_notes": upgrade_notes,
            "compatibility": compat,
        }
