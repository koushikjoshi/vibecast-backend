"""Real-Anthropic planning executor.

Uses the Anthropic Messages API directly with `claude-sonnet-4-5` + the
native `web_search_20250305` tool. Extended thinking is enabled on the
strategist call so Claude actually deliberates before emitting the
campaign plan JSON.

The CMO orchestrator pattern is emulated in Python: CMO prompt builds
the plan from Research + Strategy outputs (no recursive tool-dispatch).
This keeps hackathon-demo costs bounded and failure modes obvious.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.agents.executor_mock import PlanningInput
from app.agents.schemas import (
    CampaignPlanDraft,
    ChannelPick,
    Pillar,
    ResearchFinding,
)
from app.agents.trace import StepTracker

logger = logging.getLogger("vibecast.agents.anthropic")

# Pricing for claude-sonnet-4.5 (per 1M tokens, as of 2026-04).
_PRICING = {
    "claude-sonnet-4-5": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


# ---------------------------------------------------------------------------
# Shared craft manifesto for planning agents. Every planning agent hears
# the same voice guardrails. This is the same spirit as the artifact
# CRAFT_MANIFESTO but tuned for strategic reasoning output.
# ---------------------------------------------------------------------------

PLANNING_MANIFESTO = """# Who you are

You are a senior operator inside a supervised multi-agent marketing
system. You have a specific role in the pipeline (described below), but
you share a worldview with the other agents:

- Specificity beats abstraction every single time.
- Opinions are required. Mushy neutral output is worse than wrong output
  because it gives the reviewer nothing to push against.
- Evidence over assertion. If you cannot point to source material or a
  search result, do not make the claim.

# Non-negotiable voice rules

- No "revolutionize", "game-changing", "leverage", "unlock", "seamless",
  "cutting-edge", "best-in-class", "robust", "empower", "solution"
  (unless quoting the product's own doc).
- No "in today's rapidly evolving landscape" or variants. They are
  markers of AI-generated filler.
- Avoid three-item lists by default. If you have four useful points,
  write four. If two, write two.
- Sentences are tight. Adjectives must carry information.

# Output contract

When asked for JSON, emit exactly one JSON object with the schema
provided. No prose before or after. No markdown fences. Strings may
contain Markdown only if the schema says so."""


def _cost(model: str, tokens_in: int, tokens_out: int) -> float:
    in_rate, out_rate = _PRICING.get(model, _PRICING["claude-sonnet-4-5"])
    return round((tokens_in * in_rate + tokens_out * out_rate) / 1_000_000, 4)


def _format_sources(inputs: PlanningInput) -> str:
    blocks: list[str] = []
    for i, s in enumerate(inputs.sources, 1):
        body = s.normalized_text or s.raw_input or ""
        blocks.append(f"[{i}] type={s.type}\n{body[:2000]}")
    return "\n\n".join(blocks)[:12000]


def _format_brand(inputs: PlanningInput) -> str:
    b = inputs.brand_kit
    return json.dumps(
        {
            "positioning": b.positioning,
            "target_icp": b.target_icp,
            "tone": json.loads(b.tone_json or "{}"),
            "banned_phrases": json.loads(b.banned_phrases_json or "[]"),
            "required_disclaimers": json.loads(b.required_disclaimers_json or "[]"),
            "competitor_policy": b.competitor_policy,
        },
        indent=2,
    )


def _format_competitors(inputs: PlanningInput) -> str:
    return "\n".join(
        f"- {c.name} ({c.website_url})" for c in inputs.competitors
    ) or "(none provided)"


async def run_planning_anthropic(
    tracker: StepTracker,
    inputs: PlanningInput,
) -> CampaignPlanDraft:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package not installed") from exc

    client = anthropic.AsyncAnthropic(api_key=api_key)
    model = os.getenv("ANTHROPIC_PLANNING_MODEL", "claude-sonnet-4-5")

    project = inputs.project
    brand_summary = _format_brand(inputs)
    source_corpus = _format_sources(inputs)
    competitors_list = _format_competitors(inputs)

    tracker.log("cmo", f"CMO booted with Anthropic {model} for '{project.name}'")

    # --- Agent 1: brief-intake -----------------------------------------------
    intake_step = tracker.start(
        "brief-intake",
        tool="Read",
        model="claude-haiku-4-5",
        input_data={"sources": len(inputs.sources)},
    )
    try:
        intake_resp = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1200,
            system=(
                PLANNING_MANIFESTO
                + "\n\n# Your role: brief-intake agent\n\n"
                "You are the first agent in the pipeline. Your job is to "
                "read everything the user uploaded about this launch and "
                "extract the dense signal the rest of the team will build "
                "on. You are the memory of this project — get this wrong "
                "and everything downstream is wrong.\n\n"
                "# Do this\n"
                "1. Read all source material carefully. Note: named "
                "entities (products, customers, features), explicit "
                "numbers, direct quotes, dates, launch scope.\n"
                "2. Identify the 2-3 things that make this specific "
                "launch non-generic. These are the 'signals' other "
                "agents will sharpen into positioning.\n"
                "3. Extract 6-10 lowercase keywords that downstream "
                "market research should pursue. These should be "
                "specific queries a smart analyst would google, not "
                "generic category words. Good: 'multi-agent marketing "
                "automation B2B'. Bad: 'marketing', 'ai'.\n\n"
                "# Output\n"
                "Return ONE JSON object as the final line, no prose "
                "after it, with keys:\n"
                "- `summary`: 2-3 sentences, dense, specific, "
                "includes at least one concrete detail from the source.\n"
                "- `signals`: array of 2-3 strings describing what "
                "makes this launch genuinely interesting.\n"
                "- `keywords`: array of 6-10 lowercase phrases (not "
                "single generic words) for downstream search.\n"
                "- `evidence_gaps`: array of 0-3 specific facts the "
                "team should try to discover via web research."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Project name: {project.name}\n"
                        f"Launch date: {project.launch_date}\n\n"
                        f"Source material (verbatim from uploads):\n\n{source_corpus}\n\n"
                        "Now emit the JSON object."
                    ),
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        tracker.fail(intake_step, error=str(exc))
        raise

    intake_text = intake_resp.content[0].text if intake_resp.content else "{}"
    intake_json = _extract_json(intake_text) or {
        "summary": intake_text[:400],
        "signals": [],
        "keywords": [],
        "evidence_gaps": [],
    }
    usage = intake_resp.usage
    tracker.succeed(
        intake_step,
        output_data=intake_json,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        cost_usd=_cost("claude-haiku-4-5", usage.input_tokens, usage.output_tokens),
    )

    # --- Agent 2: market-researcher (web search) -----------------------------
    research_step = tracker.start(
        "market-researcher",
        tool="web_search",
        model=model,
        input_data={"keywords": intake_json.get("keywords", [])},
    )
    try:
        research_resp = await client.messages.create(
            model=model,
            max_tokens=2500,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 5,
                }
            ],
            system=(
                PLANNING_MANIFESTO
                + "\n\n# Your role: market-researcher agent\n\n"
                "You have live web search. Use it to surface findings "
                "that will sharpen the launch positioning and strategy. "
                "You are NOT writing marketing copy — you are gathering "
                "citeable facts the launch-strategist will build on.\n\n"
                "# Research priorities (in order)\n"
                "1. Competitor moves in the last 60 days that affect "
                "this launch's positioning.\n"
                "2. Recent category shifts, funding news, or analyst "
                "commentary that changes the story.\n"
                "3. Specific data points the strategist can quote "
                "(numbers, recent events, customer quotes from public "
                "sources).\n"
                "4. Evidence for or against any `evidence_gaps` "
                "surfaced in the intake step.\n\n"
                "# Quality rules for findings\n"
                "- Each claim is a single atomic fact, cite-worthy. "
                "Not 'the market is big' but '72% of Series-B B2B "
                "companies added a PMM headcount in 2025, up from 44% "
                "in 2023 (Lenny\\'s survey, Jan 2026)'.\n"
                "- Include source URL + source title for every "
                "finding. If you can't cite it, don't include it.\n"
                "- Prefer primary sources (company blog posts, "
                "founder tweets with context, official docs) over "
                "secondary aggregators.\n"
                "- Never include a finding you half-invented to fill "
                "a slot. 3 real findings beat 6 mushy ones.\n\n"
                "# Output\n"
                "Run up to 5 targeted web searches. Then emit ONE JSON "
                'object: {"findings": [{"claim": string, "source_url": '
                'string, "source_title": string}, ...]}. 3-5 findings. '
                "No prose before or after the JSON."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Project: {project.name}\n"
                        f"Intake summary: {intake_json.get('summary', '')}\n"
                        f"Intake signals: {intake_json.get('signals', [])}\n"
                        f"Evidence gaps to fill if possible: "
                        f"{intake_json.get('evidence_gaps', [])}\n"
                        f"Keywords to pursue: "
                        f"{', '.join(intake_json.get('keywords', [])[:8])}\n\n"
                        f"Known competitors:\n{competitors_list}\n\n"
                        "Run your searches, then emit the findings JSON."
                    ),
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        tracker.fail(research_step, error=str(exc))
        raise

    research_text = _final_text(research_resp)
    research_json = _extract_json(research_text) or {"findings": []}
    usage = research_resp.usage
    findings = [
        ResearchFinding(**f) for f in research_json.get("findings", [])
        if isinstance(f, dict) and f.get("claim")
    ][:6]
    tracker.succeed(
        research_step,
        output_data={"findings": [f.model_dump() for f in findings]},
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        cost_usd=_cost(model, usage.input_tokens, usage.output_tokens),
    )

    # --- Agent 3: launch-strategist / CMO synthesis --------------------------
    strategy_step = tracker.start(
        "launch-strategist",
        tool="submit_campaign_plan",
        model=model,
        input_data={"findings": len(findings)},
    )

    strategist_system = (
        PLANNING_MANIFESTO
        + "\n\n# Your role: launch-strategist + CMO synthesis\n\n"
        "You are the CMO. Intake and research have handed you their "
        "output. You now produce the Campaign Plan — the document that "
        "will bind every downstream artifact (blog, press, social, "
        "emails, battle card, podcast).\n\n"
        "This is the single most important object in the pipeline. "
        "Every artifact generator will consume `positioning`, "
        "`pillars`, `audience_refinement`, `channel_selection`, "
        "`competitor_angle`, `urgency_framing` and build from them. "
        "If these are generic, every downstream artifact is generic.\n\n"
        "# Craft rules\n"
        "## positioning (string)\n"
        "ONE sentence. Max 28 words. Structure: '[Product] is the "
        "[category] that [specific mechanism] for [specific ICP].' or "
        "a better variant. Must include one concrete differentiator "
        "that is not an adjective.\n"
        "- Bad: 'We're the AI-powered solution for modern marketing "
        "teams.'\n"
        "- Good: 'VibeCast is the supervised multi-agent marketing "
        "runtime that ships 12 brand-checked artifacts per launch for "
        "Series-A B2B startups.'\n\n"
        "## pillars (array of 3 items)\n"
        "Three is the target. NOT four, not two. Each pillar has:\n"
        "- `name`: 2-4 word noun phrase in title case.\n"
        "- `message`: one sentence (18-32 words) that states the "
        "benefit AND the mechanism.\n"
        "- `proof_points`: array of 2-3 short strings. Each is a "
        "concrete fact, citeable either from source material or from "
        "the research findings. Numbers + named entities where "
        "possible.\n\n"
        "Pillars should be DIFFERENT angles on the product, not three "
        "ways of saying the same thing. Test: could a competitor "
        "claim all three pillars? If yes, rewrite until at least one "
        "pillar is uniquely yours.\n\n"
        "## audience_refinement (string)\n"
        "2-4 sentences that narrow the brand kit's ICP to THIS "
        "launch's target reader. Name a specific role, a specific "
        "company-stage, and a specific pain they are feeling this "
        "quarter.\n\n"
        "## channel_selection (array of 4-6 items)\n"
        "Each has:\n"
        "- `channel`: one of [blog, press, release_notes, x, "
        "linkedin_company, linkedin_founder, hn, product_hunt, "
        "customer_email, prospect_email, battle_card, podcast].\n"
        "- `rationale`: one sentence on WHY this channel for THIS "
        "launch. Not 'reach our audience'. Specific.\n"
        "- `expected_impact`: one short phrase ('primary traffic "
        "driver', 'objection-handling for sales', 'signal-to-investors', "
        "'brand credibility').\n\n"
        "## competitor_angle (string)\n"
        "2-3 sentences. How do we position against the specific "
        "competitors on the list? Respect the brand's "
        "`competitor_policy`. If the policy is 'no direct compare', "
        "write a category-angle instead. Never invent competitor "
        "behavior; only use what's in the provided competitor data "
        "or the research findings.\n\n"
        "## urgency_framing (string)\n"
        "2-3 sentences explaining why NOW is the right moment for "
        "this launch to matter. Ground this in market signal if "
        "research findings support it; otherwise ground it in the "
        "product's own maturation (what's finally possible today).\n\n"
        "# Output contract\n"
        "ONE JSON object. Exactly these keys: positioning, pillars, "
        "audience_refinement, channel_selection, competitor_angle, "
        "urgency_framing. No prose before or after."
    )

    try:
        strategy_resp = await client.messages.create(
            model=model,
            max_tokens=6000,
            thinking={"type": "enabled", "budget_tokens": 3500},
            temperature=1.0,
            system=strategist_system,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Project: {project.name}\n"
                        f"Launch date: {project.launch_date}\n\n"
                        f"Brand kit (immutable constraints):\n{brand_summary}\n\n"
                        f"Intake summary: {intake_json.get('summary', '')}\n"
                        f"Intake signals: {intake_json.get('signals', [])}\n\n"
                        f"Research findings (cite these by substance):\n"
                        + json.dumps([f.model_dump() for f in findings], indent=2)
                        + f"\n\nKnown competitors:\n{competitors_list}\n\n"
                        f"Source material:\n{source_corpus[:6000]}\n\n"
                        "Emit the Campaign Plan JSON object."
                    ),
                }
            ],
        )
    except Exception as exc:
        # Retry without extended thinking for older keys/tiers.
        if "thinking" in str(exc).lower():
            logger.info("strategist: extended thinking unavailable, retrying without")
            strategy_resp = await client.messages.create(
                model=model,
                max_tokens=4500,
                system=strategist_system,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Project: {project.name}\n"
                            f"Launch date: {project.launch_date}\n\n"
                            f"Brand kit:\n{brand_summary}\n\n"
                            f"Intake summary: {intake_json.get('summary', '')}\n"
                            f"Intake signals: {intake_json.get('signals', [])}\n\n"
                            f"Research findings:\n"
                            + json.dumps([f.model_dump() for f in findings], indent=2)
                            + f"\n\nCompetitors:\n{competitors_list}\n\n"
                            f"Source material:\n{source_corpus[:6000]}\n\n"
                            "Emit the Campaign Plan JSON object now."
                        ),
                    }
                ],
            )
        else:
            tracker.fail(strategy_step, error=str(exc))
            raise

    strategy_text = _final_text(strategy_resp)
    plan_json = _extract_json(strategy_text)
    if not plan_json:
        tracker.fail(strategy_step, error="strategist did not return JSON")
        raise RuntimeError("planning failed: strategist output was not JSON")

    usage = strategy_resp.usage
    tracker.succeed(
        strategy_step,
        output_data=plan_json,
        tokens_in=usage.input_tokens,
        tokens_out=usage.output_tokens,
        cost_usd=_cost(model, usage.input_tokens, usage.output_tokens),
    )

    plan = CampaignPlanDraft(
        positioning=plan_json.get("positioning", ""),
        pillars=[Pillar(**p) for p in plan_json.get("pillars", [])][:4],
        audience_refinement=plan_json.get("audience_refinement", ""),
        channel_selection=[
            ChannelPick(**c) for c in plan_json.get("channel_selection", [])
        ][:6],
        competitor_angle=plan_json.get("competitor_angle", ""),
        urgency_framing=plan_json.get("urgency_framing", ""),
        research_findings=findings,
    )
    tracker.log("cmo", "Campaign plan submitted and ready for approval.")
    return plan


def _final_text(resp: Any) -> str:
    for block in reversed(resp.content or []):
        if getattr(block, "type", None) == "text":
            return block.text
    return ""


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
