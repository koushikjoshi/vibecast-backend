from __future__ import annotations

import asyncio
import logging
import random
import re
from dataclasses import dataclass
from typing import Sequence

from app.agents.schemas import (
    CampaignPlanDraft,
    ChannelPick,
    Pillar,
    ResearchFinding,
)
from app.agents.trace import StepTracker
from app.models import BrandKit, Competitor, MarketingProject, ProjectSource

logger = logging.getLogger("vibecast.agents.mock")


@dataclass
class PlanningInput:
    project: MarketingProject
    sources: Sequence[ProjectSource]
    brand_kit: BrandKit
    competitors: Sequence[Competitor]


def _source_corpus(sources: Sequence[ProjectSource]) -> str:
    chunks: list[str] = []
    for s in sources:
        if s.normalized_text:
            chunks.append(s.normalized_text)
        elif s.raw_input:
            chunks.append(s.raw_input)
    return "\n\n".join(chunks)[:8000]


def _keywords(corpus: str, n: int = 8) -> list[str]:
    words = re.findall(r"[A-Za-z]{4,}", corpus.lower())
    stop = {
        "this", "that", "with", "from", "your", "have", "will", "they", "them",
        "about", "because", "which", "where", "there", "their", "some", "more",
        "into", "than", "also", "been", "just", "like", "when", "what", "over",
        "such", "these", "those", "would", "could", "should", "much", "many",
        "most", "only", "make", "made", "across", "every",
    }
    counts: dict[str, int] = {}
    for w in words:
        if w in stop:
            continue
        counts[w] = counts.get(w, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:n]]


async def run_planning_mock(
    tracker: StepTracker,
    inputs: PlanningInput,
) -> CampaignPlanDraft:
    project = inputs.project
    brand = inputs.brand_kit
    competitors = inputs.competitors
    corpus = _source_corpus(inputs.sources)

    tracker.log("cmo", f"CMO orchestrator booted for '{project.name}'")

    intake = tracker.start(
        "brief-intake",
        tool="Read",
        model="haiku",
        input_data={
            "sources": len(inputs.sources),
            "chars": len(corpus),
        },
    )
    await asyncio.sleep(random.uniform(0.6, 1.0))
    keywords = _keywords(corpus)
    summary_sentences = re.split(r"(?<=[.!?])\s+", corpus.strip())[:3]
    source_summary = " ".join(summary_sentences) or (
        f"{project.name} is a new launch with {len(inputs.sources)} source document(s)."
    )
    tracker.succeed(
        intake,
        output_data={
            "summary": source_summary[:400],
            "keywords": keywords,
        },
        tokens_in=random.randint(1200, 2400),
        tokens_out=random.randint(280, 480),
        cost_usd=0.004,
    )

    competitor_names = [c.name for c in competitors] or ["the incumbent vendors"]

    research = tracker.start(
        "market-researcher",
        tool="WebSearch",
        model="sonnet",
        input_data={
            "queries": [
                f"{project.name} launch positioning",
                f"{keywords[0] if keywords else 'B2B'} competitive landscape",
                f"{competitor_names[0]} pricing and features",
            ],
        },
    )
    await asyncio.sleep(random.uniform(1.2, 1.8))
    findings = [
        ResearchFinding(
            claim=(
                f"Buyers in the {brand.target_icp or 'B2B SaaS'} segment "
                f"are comparing {project.name} primarily against "
                f"{', '.join(competitor_names[:2])}."
            ),
            source_url="https://g2.com/categories/marketing-platforms",
            source_title="G2 · Marketing Platforms Grid Report",
        ),
        ResearchFinding(
            claim=(
                "Generative-AI-native buyers cite speed-to-first-campaign "
                "and brand safety as the top two evaluation criteria."
            ),
            source_url="https://hbr.org/2025/06/ai-native-marketing-teams",
            source_title="HBR · The Rise of AI-Native Marketing Teams (2025)",
        ),
        ResearchFinding(
            claim=(
                "Over 60% of Series A B2B founders report cutting agency "
                "spend in 2026 as AI marketing copilots mature."
            ),
            source_url="https://openviewpartners.com/2026-gtm-benchmarks",
            source_title="OpenView · 2026 GTM Benchmarks",
        ),
    ]
    tracker.succeed(
        research,
        output_data={"findings": [f.model_dump() for f in findings]},
        tokens_in=random.randint(3200, 4800),
        tokens_out=random.randint(520, 780),
        cost_usd=0.021,
    )

    competitive = tracker.start(
        "competitive-intel",
        tool="WebFetch",
        model="sonnet",
        input_data={
            "competitors": competitor_names,
            "urls": [c.website_url for c in competitors][:3],
        },
    )
    await asyncio.sleep(random.uniform(1.0, 1.4))
    competitor_angle = (
        f"Position {project.name} as the only launch-ready copilot that "
        f"respects brand policy out of the box — a direct contrast to "
        f"{competitor_names[0]}'s manual review workflow."
    )
    tracker.succeed(
        competitive,
        output_data={"competitor_angle": competitor_angle},
        tokens_in=random.randint(2100, 3200),
        tokens_out=random.randint(380, 560),
        cost_usd=0.014,
    )

    strategy = tracker.start(
        "launch-strategist",
        model="sonnet",
        input_data={"research": len(findings), "keywords": keywords},
    )
    await asyncio.sleep(random.uniform(1.0, 1.6))
    headline_keyword = (keywords[0].capitalize() if keywords else "Launch")
    positioning = (
        brand.positioning
        or f"{project.name} is the operating system for B2B marketing teams who need to ship campaigns in hours — not weeks."
    )
    pillars = [
        Pillar(
            name=f"Ship {headline_keyword} faster",
            message=(
                f"{project.name} takes a single brief and produces a full launch kit "
                "in under an hour, with every artifact brand-checked before approval."
            ),
            proof_points=[
                "12 artifacts generated per project out of the box",
                "Typical end-to-end run: 35 minutes",
            ],
        ),
        Pillar(
            name="Brand-safe by default",
            message=(
                "A dedicated Brand Guardian agent blocks banned phrases, enforces "
                "disclaimers, and flags off-voice copy — so marketing leaders keep "
                "their guardrails without slowing the team down."
            ),
            proof_points=[
                "Immutable brand-kit versions",
                "Competitor policy enforced at generation time",
            ],
        ),
        Pillar(
            name="Grounded in evidence",
            message=(
                "Every artifact cites live web research and internal sources, "
                "so sales, founders, and PR can trust the draft without rewriting it."
            ),
            proof_points=[
                "Real-time web search on every campaign plan",
                "GEO-structured blog posts optimized for AI retrieval",
            ],
        ),
    ]
    channel_selection = [
        ChannelPick(channel="Launch blog post + press release", rationale="Anchors the narrative for prospects, press, and investors.", expected_impact="high"),
        ChannelPick(channel="LinkedIn company + founder posts", rationale="Primary demand driver for ICP.", expected_impact="high"),
        ChannelPick(channel="X launch thread", rationale="Coverage in the indie/dev/AI community.", expected_impact="medium"),
        ChannelPick(channel="Customer + prospect email", rationale="Re-engage existing pipeline.", expected_impact="high"),
        ChannelPick(channel="Podcast episode", rationale="Ambient awareness via evergreen audio.", expected_impact="medium"),
    ]
    urgency = (
        f"Launch-day window: {project.launch_date or 'TBD'}. Pair press + blog + "
        "LinkedIn + email within a 4-hour window to compound reach."
    )
    audience = (
        brand.target_icp
        or "Seed/Series-A B2B SaaS teams led by a founder or first PMM hire."
    )

    tracker.succeed(
        strategy,
        output_data={
            "positioning": positioning,
            "pillars": [p.model_dump() for p in pillars],
        },
        tokens_in=random.randint(2800, 3800),
        tokens_out=random.randint(720, 960),
        cost_usd=0.019,
    )

    cmo_step = tracker.start(
        "cmo",
        tool="submit_campaign_plan",
        model="sonnet",
        input_data={"phase": "synthesis"},
    )
    await asyncio.sleep(random.uniform(0.6, 0.9))
    plan = CampaignPlanDraft(
        positioning=positioning,
        pillars=pillars,
        audience_refinement=audience,
        channel_selection=channel_selection,
        competitor_angle=competitor_angle,
        urgency_framing=urgency,
        research_findings=findings,
    )
    tracker.succeed(
        cmo_step,
        output_data=plan.model_dump(),
        tokens_in=random.randint(1400, 2100),
        tokens_out=random.randint(820, 1100),
        cost_usd=0.011,
    )
    tracker.log("cmo", "Campaign plan submitted and ready for approval.")
    return plan
