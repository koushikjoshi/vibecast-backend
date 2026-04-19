from __future__ import annotations

import json
from typing import Any, Sequence

from app.agents.artifacts.base import GenContext


def plan_pillars(ctx: GenContext) -> list[dict]:
    try:
        return json.loads(ctx.plan.pillars_json or "[]")
    except json.JSONDecodeError:
        return []


def plan_channels(ctx: GenContext) -> list[dict]:
    try:
        return json.loads(ctx.plan.channel_selection_json or "[]")
    except json.JSONDecodeError:
        return []


def brand_voice(ctx: GenContext) -> str:
    try:
        tone = json.loads(ctx.brand_kit.tone_json or "{}")
    except json.JSONDecodeError:
        tone = {}
    return tone.get("voice") or "clear, confident, evidence-first"


def source_text(ctx: GenContext, max_chars: int = 6000) -> str:
    chunks: list[str] = []
    for s in ctx.sources:
        if s.normalized_text:
            chunks.append(s.normalized_text)
        elif s.raw_input:
            chunks.append(s.raw_input)
    return ("\n\n".join(chunks))[:max_chars]


def competitor_names(ctx: GenContext) -> list[str]:
    return [c.name for c in ctx.competitors]


def target_competitor(ctx: GenContext) -> str | None:
    if ctx.project.target_competitor_id:
        for c in ctx.competitors:
            if c.id == ctx.project.target_competitor_id:
                return c.name
    return competitor_names(ctx)[0] if ctx.competitors else None


def pillar_lines(ctx: GenContext) -> list[str]:
    lines: list[str] = []
    for p in plan_pillars(ctx):
        name = p.get("name", "")
        message = p.get("message", "")
        if name and message:
            lines.append(f"{name}: {message}")
    return lines


def brand_positioning(ctx: GenContext) -> str:
    return ctx.plan.positioning or ctx.brand_kit.positioning or ctx.project.name


def launch_date(ctx: GenContext) -> str:
    return ctx.project.launch_date.isoformat() if ctx.project.launch_date else "TBD"


def format_list(items: Sequence[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


def first_n(items: Sequence[Any], n: int) -> list[Any]:
    return list(items[:n])
