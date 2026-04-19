from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable

from app.models import BrandKit, BrandVerdict


@dataclass
class BrandFinding:
    verdict: str
    rule: str
    note: str
    section_ref: str = ""
    suggested_rewrite: str | None = None


@dataclass
class BrandCheckResult:
    verdict: str
    findings: list[BrandFinding]

    @property
    def passed(self) -> bool:
        return self.verdict != BrandVerdict.block.value

    def to_summary(self) -> dict:
        return {
            "verdict": self.verdict,
            "findings": [f.__dict__ for f in self.findings],
        }


def _iter_fields(payload: dict) -> Iterable[tuple[str, str]]:
    if not isinstance(payload, dict):
        return []
    stack: list[tuple[str, object]] = list(payload.items())
    while stack:
        key, value = stack.pop()
        if isinstance(value, str):
            yield key, value
        elif isinstance(value, dict):
            stack.extend(value.items())
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str):
                    yield f"{key}[{i}]", item
                elif isinstance(item, (dict, list)):
                    stack.append((f"{key}[{i}]", item))


def check(payload: dict, brand: BrandKit) -> BrandCheckResult:
    try:
        banned = json.loads(brand.banned_phrases_json or "[]")
    except json.JSONDecodeError:
        banned = []
    try:
        disclaimers = json.loads(brand.required_disclaimers_json or "[]")
    except json.JSONDecodeError:
        disclaimers = []

    findings: list[BrandFinding] = []

    for key, text in _iter_fields(payload):
        lower = text.lower()
        for phrase in banned:
            if not phrase:
                continue
            if re.search(rf"\b{re.escape(str(phrase).lower())}\b", lower):
                findings.append(
                    BrandFinding(
                        verdict=BrandVerdict.warn.value,
                        rule="banned_phrase",
                        note=f"'{phrase}' is banned by the brand kit.",
                        section_ref=key,
                        suggested_rewrite=None,
                    )
                )

    joined = "\n".join(text for _, text in _iter_fields(payload))
    for disc in disclaimers:
        if not disc:
            continue
        key_fragment = str(disc).lower()[:20]
        if key_fragment and key_fragment not in joined.lower():
            findings.append(
                BrandFinding(
                    verdict=BrandVerdict.warn.value,
                    rule="missing_disclaimer",
                    note=f"Required disclaimer not found: {str(disc)[:80]}",
                )
            )

    if any(f.verdict == BrandVerdict.block.value for f in findings):
        verdict = BrandVerdict.block.value
    elif findings:
        verdict = BrandVerdict.warn.value
    else:
        verdict = BrandVerdict.pass_.value

    return BrandCheckResult(verdict=verdict, findings=findings)
