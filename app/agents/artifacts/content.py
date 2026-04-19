from __future__ import annotations

from app.agents.artifacts.base import ArtifactSpec, GenContext
from app.agents.artifacts._helpers import (
    brand_positioning,
    brand_voice,
    first_n,
    launch_date,
    pillar_lines,
    plan_pillars,
    target_competitor,
)
from app.models import ArtifactStudio, ArtifactType


class _Base:
    spec: ArtifactSpec

    async def generate_anthropic(self, ctx: GenContext) -> dict:
        # Thin wrapper: real-LLM generation falls back to mock until the
        # per-artifact Anthropic prompts are wired in a follow-up.
        return await self.generate_mock(ctx)


class BlogGenerator(_Base):
    spec = ArtifactSpec(
        type=ArtifactType.blog.value,
        studio=ArtifactStudio.content.value,
        title="Launch blog post (GEO-optimized)",
        description="Long-form launch blog structured for AI retrieval (GEO) and social sharing.",
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
            f"“{pillar_quote_source}” said the founding team. “Today we're "
            "shipping a system that lets a solo PMM punch several weight "
            "classes above their headcount, without trading away brand safety.”",
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
