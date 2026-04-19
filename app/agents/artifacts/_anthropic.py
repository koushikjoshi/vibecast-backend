"""Shared helper for running real Claude generation on a single artifact.

Each artifact generator declares two bits of per-type config:
  * `anthropic_schema` — a text description of the exact JSON keys the
    generator wants back. This is included verbatim in the system prompt.
  * `anthropic_instructions` — per-artifact creative guidance (tone, length
    bounds, required sections, etc.).

`generate_via_claude` then fans in the project brief + brand kit + plan +
competitor context, calls Claude Sonnet, and parses a JSON dict out of the
response. Used by every studio (content, social, lifecycle, podcast) so the
prompting pattern is uniform and debuggable.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.agents.artifacts._helpers import (
    brand_voice,
    launch_date,
    plan_channels,
    plan_pillars,
    source_text,
)
from app.agents.artifacts.base import GenContext

logger = logging.getLogger("vibecast.artifacts.anthropic")

ARTIFACT_MODEL = "claude-sonnet-4-5"


def _brand_block(ctx: GenContext) -> str:
    bk = ctx.brand_kit
    try:
        tone = json.loads(bk.tone_json or "{}")
    except json.JSONDecodeError:
        tone = {}
    try:
        banned = json.loads(bk.banned_phrases_json or "[]")
    except json.JSONDecodeError:
        banned = []
    try:
        disclaimers = json.loads(bk.required_disclaimers_json or "[]")
    except json.JSONDecodeError:
        disclaimers = []
    return json.dumps(
        {
            "voice": tone.get("voice") or brand_voice(ctx),
            "positioning": bk.positioning,
            "target_icp": bk.target_icp,
            "banned_phrases": banned,
            "required_disclaimers": disclaimers,
            "competitor_policy": bk.competitor_policy,
            "legal_footer": bk.legal_footer,
        },
        indent=2,
    )


def _plan_block(ctx: GenContext) -> str:
    return json.dumps(
        {
            "positioning": ctx.plan.positioning,
            "pillars": plan_pillars(ctx),
            "audience_refinement": ctx.plan.audience_refinement,
            "channel_selection": plan_channels(ctx),
            "competitor_angle": ctx.plan.competitor_angle,
            "urgency_framing": ctx.plan.urgency_framing,
        },
        indent=2,
    )


def _competitor_block(ctx: GenContext) -> str:
    if not ctx.competitors:
        return "(none)"
    return "\n".join(f"- {c.name} ({c.website_url})" for c in ctx.competitors)


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    # Strip common ```json fences
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


async def generate_via_claude(
    ctx: GenContext,
    *,
    artifact_type: str,
    studio: str,
    title: str,
    anthropic_schema: str,
    anthropic_instructions: str,
    max_tokens: int = 2500,
) -> dict:
    """Call Claude Sonnet to generate a structured artifact payload.

    Raises RuntimeError on missing key, import failure, or unparseable output
    so the caller can fall back to the mock generator.
    """

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package not installed") from exc

    client = anthropic.AsyncAnthropic(api_key=api_key)

    system_prompt = (
        f"You are a senior B2B marketing specialist producing a single "
        f"`{artifact_type}` artifact for the `{studio}` studio inside the "
        f"VibeCast agentic marketing system.\n\n"
        f"Artifact title: {title}\n\n"
        f"# Output contract\n"
        f"Respond with a SINGLE JSON object and nothing else. No prose before "
        f"or after. No markdown fences. No comments.\n\n"
        f"The JSON object MUST contain these keys (extra keys are forbidden):\n"
        f"{anthropic_schema}\n\n"
        f"# Creative instructions\n"
        f"{anthropic_instructions}\n\n"
        f"# Hard constraints\n"
        f"- Respect the brand voice, banned phrases, and required disclaimers "
        f"provided below. Do not output any banned phrase, even in paraphrase.\n"
        f"- If the brand's competitor_policy is `name-only`, reference "
        f"competitors by name without trashing them.\n"
        f"- Never fabricate citations, stats, or customer quotes. If you need "
        f"evidence, base it only on the source material provided.\n"
        f"- Write in the brand's voice, not a generic AI-marketing tone.\n"
    )

    user_prompt = (
        f"# Project\n"
        f"name: {ctx.project.name}\n"
        f"launch_date: {launch_date(ctx)}\n\n"
        f"# Brand kit\n{_brand_block(ctx)}\n\n"
        f"# Campaign plan\n{_plan_block(ctx)}\n\n"
        f"# Competitors\n{_competitor_block(ctx)}\n\n"
        f"# Source material (truncated)\n{source_text(ctx, max_chars=8000)}\n\n"
        f"Now emit the single JSON object for the `{artifact_type}` artifact."
    )

    resp = await client.messages.create(
        model=ARTIFACT_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = ""
    for block in resp.content or []:
        if getattr(block, "type", None) == "text":
            text += block.text

    parsed = _extract_json(text)
    if parsed is None:
        logger.warning(
            "artifact %s: claude returned non-JSON output (len=%d)", artifact_type, len(text)
        )
        raise RuntimeError(f"claude did not return JSON for artifact {artifact_type}")
    return parsed
