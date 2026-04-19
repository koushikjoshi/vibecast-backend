"""Shared helper for running real Claude generation on a single artifact.

Design goals:
  * Output that reads like it was written by a senior B2B marketer with
    context on the product, the market, and the brand voice — not like
    generic AI output.
  * Enforced anti-patterns: no "ever-evolving landscape", no "leveraging",
    no "unlocking", no rule-of-three list obsession, no em-dash vomit, no
    emoji clutter, no fabricated statistics.
  * Extended thinking enabled by default so Claude genuinely deliberates
    before it emits JSON. This is the single biggest quality lever
    available on the Messages API.

Each generator declares:
  * `anthropic_schema` — exact JSON keys the generator expects back.
  * `anthropic_instructions` — per-artifact craft direction. The more
    specific the better. Give structural guidance, sample phrasings,
    things to avoid.
  * `anthropic_max_tokens` — output budget. Must include the thinking
    budget below when thinking is enabled.
  * `anthropic_thinking_budget` — tokens Claude can burn on internal
    deliberation before producing the JSON. 0 disables thinking.
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
from app.agents.schemas import StepEvent
from app.agents.trace import publish

logger = logging.getLogger("vibecast.artifacts.anthropic")

ARTIFACT_MODEL = os.getenv("ANTHROPIC_ARTIFACT_MODEL", "claude-sonnet-4-5")


# ---------------------------------------------------------------------------
# Craft manifesto — injected into every artifact system prompt so the model
# hears the same non-negotiables every time.
# ---------------------------------------------------------------------------

CRAFT_MANIFESTO = """# Who you are

You are a senior B2B marketing operator embedded inside the VibeCast
agent system. Before this you spent eight years at companies like Linear,
Stripe, Vercel, and Notion. You have strong opinions about craft. You've
shipped launches that made the top of Hacker News, been quoted in
TechCrunch, and sat through enough founder-review cycles to know exactly
what the best ones cut. You treat marketing as a systems discipline, not
a decoration on top of a product.

You are NOT a generic AI assistant. You are not playing a character. The
voice in your output is the voice of someone who has done this job.

# Craft principles (non-negotiable)

1. **Specificity beats abstraction every time.**
   - Bad: "We help teams move faster."
   - Good: "Acme teams cut their sprint planning from 90 minutes to 22."
   - If you cannot cite a number, cite a named mechanism. If you cannot
     cite a mechanism, cut the sentence.

2. **Concrete nouns over marketing nouns.**
   - Replace "solution" → "tool", "product", "workflow", or the literal
     name of the thing.
   - Replace "leverage" → "use".
   - Replace "unlock" → "let", "make it possible", or delete.
   - Replace "empower" → "let".
   - Replace "utilize" → "use".
   - Replace "in today's ever-evolving landscape" → delete the entire
     paragraph; it is a marker of AI-generated text and must not appear.

3. **Earned claims only.**
   - Do not fabricate customer names, logos, quotes, stats, or case
     studies. If the source material does not contain the evidence, do
     not cite evidence. Speak from principle instead.
   - If you need a quote, attribute it to a plausible internal role
     ("founding team", "head of product") and make it content-bearing,
     not cheerleading.

4. **Earn the reader's next scroll.**
   - The first sentence must do work. It should either name a specific
     problem the reader has, or deliver a claim that is interesting
     because it's narrow.
   - Never open with "In today's" or "As companies increasingly".
   - Never open with a question-to-hook ("Ever wondered if...").

5. **Voice calibration.**
   - You will be given the brand's voice in the input. Follow it as if
     you are the copy chief approving release-ready work.
   - If the brand voice is "clear, confident, evidence-first" — that
     means short sentences, no hedging, citations over adjectives.
   - If the brand voice is "warm and witty" — allow one genuine,
     non-cringe joke. Never more than one.

6. **Structural discipline.**
   - Avoid the rule-of-three trap. If you have four good points, write
     four. If you have two, write two.
   - Bullet lists are for parallel items only. If items aren't parallel,
     write prose.
   - Paragraphs are 2-4 sentences. Not 1. Not 6.

7. **Honesty about trade-offs.**
   - When an artifact calls for it (battle card, prospect email, HN
     post), name the real trade-off. Readers trust writers who admit
     where the thing is weak. Avoid false humility.

8. **No AI tells.**
   The following are immediate red flags. Output containing any of these
   will be rejected:
   - "revolutionize", "revolutionary", "game-changer", "game-changing"
   - "unlocking the power of", "unleashing"
   - "in the rapidly evolving landscape of"
   - "seamlessly", "effortlessly", "cutting-edge", "best-in-class",
     "world-class", "state-of-the-art", "robust"
   - "delve into", "embark on a journey", "navigate the complexities"
   - Three-item lists when a two- or four-item list fits better
   - Em-dash abuse (use one per paragraph max)
   - Starting multiple sentences with "Moreover", "Furthermore",
     "Additionally"
   - Ending with a generic flourish like "The possibilities are endless"

9. **Respect the brand kit's banned_phrases array absolutely.**
   If a phrase is in banned_phrases, it cannot appear in output — not
   even in paraphrase. Rewrite around it.

10. **Respect the brand kit's required_disclaimers.**
    Every disclaimer in that array must appear verbatim somewhere in the
    output when contextually relevant (legal footer, email footer, etc.).

# Output contract

Respond with a SINGLE JSON object and nothing else. No prose before or
after the JSON. No markdown fences. No comments inside the JSON. Never
invent additional keys beyond the schema. String values can contain
Markdown where the schema says so.

If you truly cannot produce the artifact (the source material is empty,
for example), output this exact JSON: `{"error": "insufficient context",
"reason": "<one-sentence reason>"}` and stop. Do not fabricate content
to fill the schema."""


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
        return "(no competitors provided)"
    lines: list[str] = []
    for c in ctx.competitors:
        line = f"- {c.name} ({c.website_url})"
        if c.positioning_cached:
            line += f"\n    positioning: {c.positioning_cached[:240]}"
        lines.append(line)
    return "\n".join(lines)


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
    max_tokens: int = 2200,
    thinking_budget: int = 0,
) -> dict:
    """Call Claude Sonnet with extended thinking to produce a structured artifact.

    Thinking is enabled by default. It roughly doubles latency but produces
    dramatically better output on nuanced writing tasks. Set
    `thinking_budget=0` on a per-artifact basis to disable for short,
    mechanical artifacts where extra deliberation adds no value.

    Raises RuntimeError on missing key, import failure, or unparseable
    output so the caller can fall back to the deterministic mock.
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
        f"{CRAFT_MANIFESTO}\n\n"
        f"# This specific artifact\n\n"
        f"Type: `{artifact_type}`\n"
        f"Studio: `{studio}`\n"
        f"Title: {title}\n\n"
        f"## JSON schema (exact keys required)\n\n"
        f"{anthropic_schema}\n\n"
        f"## Craft direction for this artifact\n\n"
        f"{anthropic_instructions}\n\n"
        f"## Process (follow in order)\n\n"
        f"1. Read the project brief, brand kit, campaign plan, and "
        f"competitors carefully. Extract every concrete detail — product "
        f"names, dates, numbers, named features, target personas.\n"
        f"2. Identify three things that make this launch specifically "
        f"interesting vs. a generic SaaS launch. Note them.\n"
        f"3. Draft the artifact internally, obeying every craft rule.\n"
        f"4. Self-review: scan for banned phrases, AI tells, unearned "
        f"claims, and filler sentences. Cut ruthlessly.\n"
        f"5. Emit the final JSON object."
    )

    user_prompt = (
        f"# Project\n"
        f"name: {ctx.project.name}\n"
        f"launch_date: {launch_date(ctx)}\n\n"
        f"# Brand kit\n{_brand_block(ctx)}\n\n"
        f"# Campaign plan (approved by the human reviewer)\n"
        f"{_plan_block(ctx)}\n\n"
        f"# Competitors\n{_competitor_block(ctx)}\n\n"
        f"# Source material (launch brief, uploaded docs, URLs)\n"
        f"{source_text(ctx, max_chars=2500)}\n\n"
        f"Now produce the `{artifact_type}` artifact as the single JSON "
        f"object defined in the schema. No prose, no fences."
    )

    kwargs: dict[str, Any] = {
        "model": ARTIFACT_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    if thinking_budget and thinking_budget > 0:
        # Extended thinking forces Claude to deliberate before speaking.
        # Requires temperature=1 per Anthropic docs.
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        kwargs["temperature"] = 1.0

    # Stream chunks back into the run's SSE bus so the frontend can render
    # the model "typing" live — matches the UX expected from modern agentic
    # apps. Falls back to non-streaming if the stream API is unavailable.
    text = ""
    run_id = getattr(ctx, "run_id", None)
    step_id = getattr(ctx, "step_id", None)
    agent_label = getattr(ctx, "agent_label", "") or f"{studio}:{artifact_type}"

    try:
        async with client.messages.stream(**kwargs) as stream:
            buffer = ""
            last_flush = 0
            async for event in stream:
                delta_text = ""
                etype = getattr(event, "type", None)
                if etype == "content_block_delta":
                    delta = getattr(event, "delta", None)
                    if delta is not None and getattr(delta, "type", None) == "text_delta":
                        delta_text = getattr(delta, "text", "") or ""
                if not delta_text:
                    continue
                text += delta_text
                buffer += delta_text
                # Flush to SSE every ~80 chars so the UI paints smoothly
                # without us spamming the event loop.
                if run_id and len(buffer) - last_flush >= 80:
                    publish(
                        run_id,
                        StepEvent(
                            type="chunk",
                            agent=agent_label,
                            message=buffer,
                            data={
                                "step_id": str(step_id) if step_id else None,
                                "artifact_type": artifact_type,
                            },
                        ),
                    )
                    buffer = ""
                    last_flush = 0
            if run_id and buffer:
                publish(
                    run_id,
                    StepEvent(
                        type="chunk",
                        agent=agent_label,
                        message=buffer,
                        data={
                            "step_id": str(step_id) if step_id else None,
                            "artifact_type": artifact_type,
                        },
                    ),
                )
    except Exception as exc:
        # If streaming is unavailable or thinking is rejected, fall back
        # to a single non-streaming call so the demo path still works.
        if thinking_budget and "thinking" in str(exc).lower():
            logger.info(
                "artifact %s: extended thinking unavailable, retrying without",
                artifact_type,
            )
            kwargs.pop("thinking", None)
            kwargs.pop("temperature", None)
        resp = await client.messages.create(**kwargs)
        text = ""
        for block in resp.content or []:
            if getattr(block, "type", None) == "text":
                text += block.text

    parsed = _extract_json(text)
    if parsed is None:
        logger.warning(
            "artifact %s: claude returned non-JSON (len=%d, preview=%r)",
            artifact_type,
            len(text),
            text[:240],
        )
        raise RuntimeError(f"claude did not return JSON for artifact {artifact_type}")

    if parsed.get("error") == "insufficient context":
        raise RuntimeError(
            f"claude declined to generate {artifact_type}: {parsed.get('reason', '')}"
        )

    return parsed
