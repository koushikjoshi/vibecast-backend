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
    # Tuned for Anthropic Tier-1 TPM (30k input tokens/min). Extended
    # thinking is off by default for artifacts; enable per-artifact only
    # where the creative lift is huge (e.g. the flagship blog post).
    anthropic_max_tokens: ClassVar[int] = 2000
    anthropic_thinking_budget: ClassVar[int] = 0

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
                thinking_budget=self.anthropic_thinking_budget,
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
    anthropic_max_tokens = 3600
    anthropic_thinking_budget = 0
    anthropic_schema = (
        "{\n"
        '  "headline": string (SEO title, 55-72 chars, front-loaded keyword),\n'
        '  "subhead": string (dek, 140-190 chars, extends the headline\'s promise with a concrete mechanism),\n'
        '  "tldr": array of 3-5 string bullets. Each bullet is a standalone fact Claude or ChatGPT could cite verbatim to answer "what is <product>?",\n'
        '  "sections": array of 5-7 {"heading": string (phrased as a search-like query when possible, e.g. "How does X handle Y?"), "body": string (150-240 words of markdown, can include nested bullets)},\n'
        '  "faq": array of 4-6 {"q": string (literal user-phrased question, includes product name), "a": string (60-110 words)},\n'
        '  "cta": {"label": string (verb-first, <=32 chars), "href": string},\n'
        '  "geo_schema": {"@context": "https://schema.org", "@type": "Article", "headline": string, "description": string, "datePublished": string ISO date YYYY-MM-DD, "about": string},\n'
        '  "voice_note": string (one sentence explaining the specific voice choices you made for this post and why)\n'
        "}"
    )
    anthropic_instructions = (
        "This is the flagship launch post. It gets syndicated to the "
        "homepage, shared on LinkedIn by the founder, and — crucially — "
        "gets crawled by ChatGPT, Perplexity, Claude, and Gemini to "
        "answer questions about the product. Structure accordingly.\n\n"
        "# Structure\n"
        "- Open with the TL;DR section (the `tldr` array). This is what "
        "large language models will quote. Each bullet must be factual, "
        "self-contained, and include the product name once.\n"
        "- Lead section: 'Why we built this' or similar. Tell a real, "
        "specific story from the founder's POV. One paragraph. No "
        "abstraction.\n"
        "- Middle sections: map one to each campaign pillar. Heading is "
        "phrased as a search query users actually type ('How does X "
        "handle Y?'). Body proves the claim with a mechanism, a "
        "workflow description, or a concrete before/after.\n"
        "- Penultimate section: 'What's not in this release' or 'What "
        "we didn't build'. Honest trade-offs build trust and are rare in "
        "AI-written copy — they're a strong differentiator.\n"
        "- Final section: what happens next for readers who try it.\n\n"
        "# Voice\n"
        "- Sentences average 14-18 words. Vary rhythm. Break up long "
        "paragraphs with a single short sentence for emphasis.\n"
        "- First-person plural ('we') for the company. First-person "
        "singular only in quoted founder speech.\n"
        "- Never write 'In today's fast-paced world' or any variant.\n"
        "- Never open a section with 'Let's dive in' or 'Let's explore'.\n\n"
        "# FAQ section craft\n"
        "The FAQ is not filler. It is the most-retrieved-by-AI section of "
        "the post. Questions must be phrased exactly as a user would type "
        "them into a search engine, including the product name when "
        "natural. Answers are 60-110 words, start with a direct answer, "
        "then give one mechanism and one example.\n\n"
        "# GEO schema\n"
        "`geo_schema.description` is what Google surfaces in AI overview. "
        "It should be 150-160 chars, say what the product does in plain "
        "mechanism terms, and include the product name once."
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
    anthropic_max_tokens = 2200
    anthropic_thinking_budget = 0
    anthropic_schema = (
        "{\n"
        '  "dateline": string ("CITY \u2014 Month D, YYYY" format, all caps city),\n'
        '  "headline": string (75-95 chars, inverted-pyramid style, sentence case, no hype),\n'
        '  "subheadline": string (120-160 chars that qualifies the headline with a specific mechanism or first adopter),\n'
        '  "body_paragraphs": array of 5-7 strings. Paragraph 1 is the 5W lede (200-260 chars). Paragraphs 2-3 give mechanism / differentiation. Paragraphs 4-5 give customer context / market framing. Paragraph 6-7 are forward-looking and about availability/pricing.,\n'
        '  "quote": string (single quote <= 260 chars, content-bearing, not cheerleading),\n'
        '  "quote_attribution": string ("Name, Title, Company" \u2014 invent a plausible internal named exec),\n'
        '  "second_quote": string (optional <= 240 chars quote from a customer, analyst, or partner; empty string if source material does not support one),\n'
        '  "second_quote_attribution": string (empty if no second quote),\n'
        '  "boilerplate": string (2-3 sentence "About [company]" block; concrete; no hype),\n'
        '  "contact": {"name": string, "email": string, "url": string},\n'
        '  "disclaimer": string (safe-harbor / forward-looking statement, 1-3 sentences)\n'
        "}"
    )
    anthropic_instructions = (
        "Write in the voice of a serious AP-style business press release "
        "that a wire service (Business Wire, PR Newswire) would actually "
        "distribute. This is NOT a marketing post. It is a news document.\n\n"
        "# Inverted-pyramid structure\n"
        "- Lede paragraph (first): who/what/when/where/why. One sentence, "
        "maybe two. Every noun is concrete.\n"
        "- Second paragraph: the mechanism. How does the product actually "
        "work? Two sentences.\n"
        "- Third paragraph: the problem it solves in the market today, "
        "with one specific pain point from the source material.\n"
        "- Fourth paragraph: quote from the named exec. The quote must "
        "make a content-bearing claim, not say 'we're excited'.\n"
        "- Fifth paragraph: differentiation vs. existing approaches. Name "
        "categories, not competitors (e.g. 'generative writing tools' "
        "rather than naming Jasper), unless the brand policy allows it.\n"
        "- Sixth paragraph: availability, pricing tier, geographic scope. "
        "If source material does not provide these, write 'Generally "
        "available starting <launch_date>. Pricing details at <website>.'\n"
        "- Seventh paragraph (optional): second quote from a customer or "
        "analyst. Only include if source material supports it. Leave the "
        "`second_quote` keys empty strings otherwise.\n\n"
        "# Voice\n"
        "- Third person. Past tense for the announcement ('announced "
        "today'), present tense for product descriptions.\n"
        "- No adjectives unless they carry information ('38% faster' yes; "
        "'powerful' no).\n"
        "- No phrases like 'we are thrilled to announce'. A wire service "
        "would cut that.\n"
        "- Quotes must sound like the person actually speaking, not like "
        "marketing copy. Use contractions. Use cadence.\n\n"
        "# Quote test\n"
        "Before finalizing a quote, ask: 'Would this quote make sense "
        "attributed to a different company's exec?' If yes, rewrite it "
        "until the answer is no."
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
            "subheadline": (
                f"{project.name} pairs a CMO-style orchestrator with specialist "
                "research, content, social, and podcast agents to ship a full "
                "launch kit on a single brief."
            ),
            "body_paragraphs": body,
            "quote": pillar_quote_source,
            "quote_attribution": f"Founding team, {project.name}",
            "second_quote": "",
            "second_quote_attribution": "",
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
    anthropic_max_tokens = 1600
    anthropic_thinking_budget = 0
    anthropic_schema = (
        "{\n"
        '  "version": string (semver like "1.4.0" or ISO date),\n'
        '  "release_name": string (short codename or release theme, 2-4 words, empty string if none),\n'
        '  "summary": string (one-line TL;DR of the release, <= 140 chars),\n'
        '  "highlights": array of 2-3 {"title": string, "body": string (2-3 sentences describing one flagship change, mechanism first)},\n'
        '  "bullets": array of 5-10 strings. Each begins with one of [New]/[Improved]/[Fixed]/[Changed]/[Deprecated]. Verb-first ("Added...", "Cut..."). Specific noun. No vague marketing verbs.,\n'
        '  "upgrade_notes": array of 1-3 strings describing any breaking changes or required actions. Empty array if none.,\n'
        '  "compatibility": string (one-line note on OS / version / integration requirements),\n'
        '  "credits": string (optional line thanking named contributors; empty string if source material does not support it)\n'
        "}"
    )
    anthropic_instructions = (
        "Write in the style of the best product changelogs on the "
        "internet — Linear, Stripe, Vercel, GitHub. The reader is a "
        "technical user who wants to know, in 30 seconds, what changed "
        "and whether they need to do anything about it.\n\n"
        "# Craft rules for bullets\n"
        "- Verb-first: 'Added', 'Cut', 'Rewrote', 'Fixed', 'Replaced'. "
        "Not 'We have added'.\n"
        "- Specific noun: '...SSO via Okta' not '...improved authentication'.\n"
        "- Include the interaction surface when relevant: 'on the billing "
        "page', 'in the CLI', 'in the embeddable widget'.\n"
        "- Numbers when truthful: 'cut p95 latency from 420ms to 180ms'.\n"
        "- One idea per bullet.\n\n"
        "# Highlights\n"
        "Highlights are the 2-3 bullets that deserve their own story. "
        "Each highlight is a mini-blog paragraph: open with the mechanism, "
        "then describe the user-visible effect, then mention any caveat.\n\n"
        "# Upgrade notes\n"
        "If the source material does not describe any breaking changes, "
        "leave `upgrade_notes` as an empty array. Do not manufacture "
        "fake migration steps.\n\n"
        "# Never\n"
        "- 'We're excited to announce...'\n"
        "- 'A better experience for our users'\n"
        "- 'Various improvements and bug fixes' (always be specific)"
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
            "release_name": "",
            "summary": summary,
            "highlights": [
                {
                    "title": "Agentic launch pipeline",
                    "body": (
                        "A CMO orchestrator dispatches research, strategy, "
                        "content, social, lifecycle, and podcast agents on "
                        "every launch brief. Each artifact passes through "
                        "Brand Guardian before it reaches the approval queue."
                    ),
                }
            ],
            "bullets": bullets,
            "upgrade_notes": upgrade_notes,
            "compatibility": compat,
            "credits": "",
        }
