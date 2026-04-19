"""Real-Anthropic planning executor.

Uses the Anthropic Messages API directly with `claude-sonnet-4` + the native
`web_search_20250305` tool. This module is deliberately small: it calls each
agent as a sequential API call and reports steps to the tracker so the live
trace UI behaves identically to the mock executor.

The CMO orchestrator pattern is emulated in Python: CMO prompt builds the plan
from Research + Strategy outputs (no recursive tool-dispatch). This keeps
hackathon-demo costs bounded and failure modes obvious.
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
    model = "claude-sonnet-4-5"

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
            max_tokens=800,
            system=(
                "You are the brief-intake agent. Read the project source "
                "material and produce a single-paragraph summary followed by "
                "a JSON line with keys `summary` and `keywords` (array of 6-10 "
                "lowercase strings). Output ONLY the JSON line as the final "
                "line — no prose after it."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Project: {project.name}\nLaunch: {project.launch_date}\n\n"
                        f"Source material:\n{source_corpus}\n\n"
                        "Return your JSON line now."
                    ),
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
        tracker.fail(intake_step, error=str(exc))
        raise

    intake_text = intake_resp.content[0].text if intake_resp.content else "{}"
    intake_json = _extract_json(intake_text) or {"summary": intake_text[:400], "keywords": []}
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
            max_tokens=1600,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 4,
                }
            ],
            system=(
                "You are the market-researcher agent. Use web search to gather "
                "3-5 fresh, citable claims about the launch context. Return "
                "ONLY a single JSON line: {\"findings\": [{\"claim\": ..., "
                "\"source_url\": ..., \"source_title\": ...}, ...]}."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Project: {project.name}\n"
                        f"Intake summary: {intake_json.get('summary', '')}\n"
                        f"Keywords: {', '.join(intake_json.get('keywords', [])[:8])}\n"
                        f"Competitors: {competitors_list}\n\n"
                        "Run up to 4 web searches, then emit the JSON."
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
    try:
        strategy_resp = await client.messages.create(
            model=model,
            max_tokens=3000,
            system=(
                "You are the launch-strategist + CMO synthesis agent. Produce "
                "the final Campaign Plan as a single JSON object (no prose) "
                "with EXACTLY these keys: positioning (string), pillars "
                "(array of {name, message, proof_points[]}), "
                "audience_refinement (string), channel_selection (array of "
                "{channel, rationale, expected_impact}), competitor_angle "
                "(string), urgency_framing (string). Respect the brand kit. "
                "Pillars: 3 items. Channel selection: 4-6 items."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Project: {project.name}\n"
                        f"Launch: {project.launch_date}\n\n"
                        f"Brand kit:\n{brand_summary}\n\n"
                        f"Intake summary: {intake_json.get('summary', '')}\n\n"
                        f"Research findings:\n"
                        + json.dumps([f.model_dump() for f in findings], indent=2)
                        + f"\n\nCompetitors:\n{competitors_list}\n\n"
                        "Emit the Campaign Plan JSON now."
                    ),
                }
            ],
        )
    except Exception as exc:  # noqa: BLE001
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
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
