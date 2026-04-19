"""Seed the database with an inflated, demo-ready workspace.

Creates a `pullman` workspace with a fully-filled brand kit, four
competitors with cached positioning, and a rich marketing project
containing five source documents (one-pager, engineering memo, customer
research memo, launch plan, and a press URL).

Idempotent: re-running is a no-op if the demo workspace already exists.

Run via:

    python -m app.scripts.seed_demo
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from sqlmodel import Session, select

from app.config import get_settings
from app.db import engine, init_db
from app.models import (
    BrandKit,
    BrandPreset,
    Competitor,
    MarketingProject,
    Membership,
    ProjectSource,
    ProjectState,
    Role,
    User,
    Workspace,
)

logger = logging.getLogger("vibecast.seed")

DEMO_EMAIL = "demo@vibecast.ai"
DEMO_SLUG = "pullman"
DEMO_NAME = "Pullman"


# ---------------------------------------------------------------------------
# Brand kit — the kind of depth a real Series-A B2B startup would hand to
# a PMM or copy contractor on day one. Opinionated voice, concrete banned
# phrases, two required disclaimers.
# ---------------------------------------------------------------------------

BRAND_TONE = {
    "voice": (
        "Clear, confident, evidence-first. We write like a senior engineer "
        "explaining a system to a smart friend — short sentences, concrete "
        "mechanisms, no adjective stacking. Dry humour is allowed when it "
        "lands. No cheerleading, no breathlessness, no faux urgency."
    ),
    "style_rules": [
        "Sentences average 14–18 words. Break rhythm deliberately.",
        "Lead with the mechanism, not the benefit.",
        "Name the product, name the customer role, name the metric.",
        "Never hedge with 'may' or 'can help' when you mean 'does'.",
        "Em dashes allowed, but one per paragraph max.",
    ],
    "persona": (
        "Founder / senior engineer / DX-minded PMM. Writes like Anthropic's "
        "product docs or Stripe's changelog — terse, useful, quietly witty."
    ),
}

BRAND_BANNED_PHRASES = [
    "revolutionary",
    "revolutionize",
    "game-changing",
    "best-in-class",
    "world-class",
    "seamless",
    "cutting-edge",
    "leverage",
    "unlock",
    "unleash",
    "empower",
    "robust",
    "supercharge",
    "in today's rapidly evolving landscape",
    "at the speed of thought",
]

BRAND_DISCLAIMERS = [
    "Pullman is a registered trademark of Pullman Labs, Inc.",
    "Performance numbers reflect internal benchmarks on Pullman v3 and are "
    "provided for orientation only.",
]

BRAND_VOICE_SAMPLES = [
    "Pullman v3 ships today. It tracks every agent decision — tool call, "
    "token bill, branch — in one timeline you can replay and diff.",
    "We don't ship silent features. Every public capability is in the "
    "changelog, tagged with its owner, the commit, and a video under 30s.",
    "If your agent spends $14 on a task and you can't tell which tool "
    "burned the budget, that's not an agent. That's a faith-based exercise.",
]


# ---------------------------------------------------------------------------
# Four plausible competitors in the AI observability / LLM-ops space, each
# with a one-paragraph cached positioning so the planning agents have real
# signal to work with.
# ---------------------------------------------------------------------------

COMPETITORS = [
    (
        "LangSmith",
        "https://smith.langchain.com",
        "LangSmith is LangChain's hosted tracing and evaluation platform. "
        "Strong integration with LangChain / LangGraph SDKs, enterprise-ready "
        "dashboards, heavy focus on prompt experiments and offline evals. "
        "Weakness: coupled to the LangChain runtime; less useful if your "
        "agents are written in Anthropic SDK, OpenAI SDK, or custom Python.",
    ),
    (
        "Langfuse",
        "https://langfuse.com",
        "Open-source LLM observability and evaluation. Self-hostable, strong "
        "community, solid trace viewer. Positioning: 'the Grafana of LLM "
        "apps'. Weakness: evaluation tooling is thinner than LangSmith, "
        "multi-agent visualization is early-stage.",
    ),
    (
        "Helicone",
        "https://www.helicone.ai",
        "Proxy-based LLM observability — drop in one header, see every call. "
        "Great for single-model apps. Strong dashboards, cost tracking, "
        "caching. Weakness: structurally flat — doesn't render multi-agent "
        "pipelines as graphs, doesn't treat tool calls as first-class.",
    ),
    (
        "Arize Phoenix",
        "https://phoenix.arize.com",
        "Open-source, notebook-first observability. Built for ML engineers "
        "who are now doing LLM work. Strong on span-level analysis and "
        "drift detection. Weakness: interface is optimized for ML engineers, "
        "not product or PMM teams who want to demo a trace to a buyer.",
    ),
]


# ---------------------------------------------------------------------------
# Project: Pullman v3 — Agent Observability. Five source documents, each
# written like a real internal memo: dense, specific, with numbers and
# named roles. This gives the agent pipeline something to actually sharpen.
# ---------------------------------------------------------------------------

ONE_PAGER = """\
# Pullman v3 — one-pager

## What it is
Pullman is the observability and evaluation platform for multi-agent
systems. v3 ships agent-graph tracing: every run is a DAG of agents,
tools, and LLM calls you can replay, diff, and attach evals to.

## The problem
Teams shipping production agents today work with a grab-bag of flat trace
viewers (LangSmith), proxy dashboards (Helicone), or home-grown tooling.
When an agent misbehaves in prod — a tool call explodes cost, a branch
hallucinates, a retry loop fires — debugging it is archaeology across
three tabs and a Slack thread. We shortened that loop to one URL.

## Who it's for
- Engineering leads at Series-A → Series-C B2B companies running at least
  one customer-facing agent in prod (~3–40 engineers on LLM workloads).
- ML platform teams that already adopted LangSmith but have workloads
  that run outside LangChain.
- Founders / staff engineers who built their own tracing in Postgres and
  are three months past wanting to maintain it.

## v3 feature set
1. Agent-graph trace view — every run is a DAG, not a flat list.
2. Replayable sessions — replay a trace with new prompts, diff outputs.
3. Attached evals — wire in offline evals per-step, see pass rates per
   agent, per tool, per prompt version over time.
4. Cost-per-task anomaly alerts — alert when the 95th percentile cost
   for a task type shifts > 2σ.
5. Live timeline sharing — copy a link to a trace, share with sales or
   a customer. Read-only, expires in 72h.
6. Anthropic, OpenAI, Vertex, Bedrock support in one SDK — `pip install
   pullman` and wrap your client.

## Pricing
- Starter: $0 up to 100k spans/mo, 7-day retention.
- Team: $99/mo — 2M spans/mo, 30-day retention, team workspace, shared
  dashboards.
- Scale: custom — unlimited spans, SSO, audit log, on-prem option.

## Why now
LLM workloads moved from demos to revenue in 2025. Engineering leads we
interview (n=42) say "observability" is their #1 unresolved concern above
latency and cost. The multi-agent shift — CMO pattern, routing agents,
tool-call graphs — breaks the flat-trace model that worked for single-LLM
apps. v3 is the response to that shift.

## Launch date
Next Thursday. Embargo lifts at 9am PT.
"""

ENG_MEMO = """\
# Engineering memo — Pullman v3, from @arjun

Some numbers for the launch copy. Please don't invent new ones.

**Trace write throughput (internal benchmark, single region):**
- v2: ~4,200 spans/sec sustained, p99 ingestion latency 340ms
- v3: ~11,800 spans/sec sustained, p99 ingestion latency 110ms
- The win is a rewritten ingestion path (batched writes + async fanout
  to ClickHouse + Redpanda).

**Agent-graph view perf (UI):**
- Hydration of a 400-node, 1,200-edge trace: 180ms on v3 (was 2.4s on
  v2's flat list render).
- Replay with new prompts runs on detached workers — does not block the
  UI or the production tenant's quota.

**Integration surface:**
- Official SDK for Python, TypeScript. Go and Ruby in the next quarter.
- Auto-instrumentation wrappers: Anthropic SDK, OpenAI SDK, Vertex AI,
  Bedrock, LangGraph, llamaindex.
- OTEL-compatible export — you can forward Pullman spans to Honeycomb,
  Datadog, or Grafana Tempo if you run a central pipeline.

**What we intentionally did not ship in v3:**
- No agent-authoring tooling. We are tracing, evaluating, and replaying
  — not building agents.
- No inference hosting. We don't proxy your model calls; we observe them.
- No "autonomous fix" / "AI debugger" feature. Too early, too close to
  magic.

**Customers under NDA who have been on the v3 private beta:**
- 14 companies, ~900 engineers total. Retention from v2→v3 beta: 100%.
- Named references available post-launch: Notion (via platform team),
  Vercel (via v0 team), and a Series-B fintech we'll announce Day-7.

Please prefer concrete numbers from this memo over generic claims. If a
number isn't here, don't make one up.
"""

CUSTOMER_RESEARCH = """\
# Customer interviews — summary from Priya (Head of Product)

n=42 engineering leads interviewed Feb–Mar 2026. All shipping at least
one customer-facing LLM feature. 31 of 42 had a production incident in
the last 90 days tied to agent behavior.

## Top 3 unresolved problems (by weighted rank)

1. **"We can't debug why the agent spent $14 on a single task."**
   28/42 raised this unprompted. They have cost per-run, but not
   cost-per-decision. Can't answer "which tool call, inside which
   branch, did it?".

2. **"We don't know if a prompt change made things better or worse."**
   25/42. They're shipping prompt changes by vibes + cherry-picked
   traces. They want the obvious thing: A/B on a slice of real traffic
   with a persisted eval.

3. **"Our on-call engineer gets paged for an agent misbehavior at 2am
   and has no way to replay the exact state."**
   19/42. This is the core replay feature in v3.

## Surprising findings
- Nobody brought up "latency" as a top-3 issue. Latency was table-stakes.
- 6/42 had already churned from LangSmith because they weren't using
  LangChain. The SDK lock-in is real and they resent it.
- 9/42 tried Langfuse and reverted because the trace viewer didn't
  handle multi-agent DAGs well — it flattens parallel agent spans.

## Quotes we have signed permission to use
- "We replaced three dashboards with one Pullman link in our runbook."
  — Staff engineer, fintech Series B
- "It's the first tool where the trace view looks like how I actually
  think about the system." — CTO, dev-tools startup
- "If you can't tell me which tool call blew my budget, you're a log
  aggregator, not a debugger." — Head of platform, healthcare AI
"""

LAUNCH_PLAN = """\
# Launch plan (high level)

- Thursday 9am PT: Embargo lifts. Blog post live on pullman.dev/blog.
- Thursday 9:05am PT: Founder's personal LinkedIn post goes live.
- Thursday 9:15am PT: X launch thread from @pullman.
- Thursday 10am PT: Show HN post (no commentary).
- Thursday 12pm PT: LinkedIn company post from the company page.
- Thursday 2pm PT: Customer announcement email to existing tenants.
- Friday 9am PT: Prospect nurture email to waitlist (2,400 subscribers).
- Friday 11am PT: Product Hunt launch (scheduled — not Thursday so we
  don't split attention with HN).
- Next Monday: Podcast episode drops with @arjun + founding design
  partner discussing the v2→v3 rewrite and the 11,800 spans/sec number.
- Battle card for internal AEs goes to Notion on Wednesday 4pm so sales
  can rehearse before embargo lift.

Brand guidance: never directly shit-talk competitors in public copy. Our
competitor policy is "name-only" — we name them, respect their work,
show our angle. No paragraphs about what LangSmith "gets wrong".
"""

SOURCE_URL = "https://pullman.dev/blog/v3-preview"


def _upsert_brand(session: Session, workspace_id, user_id) -> BrandKit:
    existing = session.exec(
        select(BrandKit)
        .where(BrandKit.workspace_id == workspace_id)
        .order_by(BrandKit.version.desc())
    ).first()
    if existing:
        return existing
    brand = BrandKit(
        workspace_id=workspace_id,
        version=1,
        preset=BrandPreset.professional.value,
        tone_json=json.dumps(BRAND_TONE),
        banned_phrases_json=json.dumps(BRAND_BANNED_PHRASES),
        required_disclaimers_json=json.dumps(BRAND_DISCLAIMERS),
        competitor_policy="name-only",
        pronunciation_json=json.dumps(
            [{"term": "Pullman", "ipa": "/ˈpʊlmən/", "note": "rhymes with full-man"}]
        ),
        legal_footer="© 2026 Pullman Labs, Inc. All rights reserved.",
        positioning=(
            "Pullman is the agent-graph observability platform for teams "
            "running multi-agent systems in production — replay every "
            "decision, attach evals to any step, ship prompt changes with "
            "evidence instead of vibes."
        ),
        target_icp=(
            "Engineering leads at Series-A → Series-C B2B companies "
            "(≈3–40 engineers on LLM workloads) who have graduated from "
            "a single-LLM prototype to a multi-agent or agent-with-tools "
            "system running real customer traffic."
        ),
        voice_samples_json=json.dumps(BRAND_VOICE_SAMPLES),
        created_by=user_id,
    )
    session.add(brand)
    session.flush()
    return brand


def run() -> None:
    settings = get_settings()
    init_db()

    with Session(engine) as session:
        existing_ws = session.exec(
            select(Workspace).where(Workspace.slug == DEMO_SLUG)
        ).first()
        if existing_ws is not None:
            logger.info(
                "demo workspace '%s' already present (id=%s); skipping",
                DEMO_SLUG,
                existing_ws.id,
            )
            print(f"[seed] demo workspace '{DEMO_SLUG}' already exists. skipping.")
            return

        user = session.exec(select(User).where(User.email == DEMO_EMAIL)).first()
        if user is None:
            user = User(email=DEMO_EMAIL, name="Demo User")
            session.add(user)
            session.flush()

        workspace = Workspace(
            slug=DEMO_SLUG,
            name=DEMO_NAME,
            brand_preset=BrandPreset.professional.value,
            created_by=user.id,
        )
        session.add(workspace)
        session.flush()

        session.add(
            Membership(
                workspace_id=workspace.id,
                user_id=user.id,
                role=Role.owner.value,
            )
        )

        _upsert_brand(session, workspace.id, user.id)

        for name, url, positioning in COMPETITORS:
            session.add(
                Competitor(
                    workspace_id=workspace.id,
                    name=name,
                    website_url=url,
                    positioning_cached=positioning,
                )
            )

        launch = date.today() + timedelta(days=7)
        project = MarketingProject(
            workspace_id=workspace.id,
            slug="pullman-v3-launch",
            name="Pullman v3 — Agent Observability launch",
            launch_date=launch,
            state=ProjectState.intake.value,
            source_dir_path="",
            created_by=user.id,
        )
        session.add(project)
        session.flush()

        sources_dir = Path(settings.projects_dir) / str(project.id) / "sources"
        workspace_dir = Path(settings.projects_dir) / str(project.id) / "workspace"
        sources_dir.mkdir(parents=True, exist_ok=True)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        project.source_dir_path = str(sources_dir)

        def _write_and_register(
            filename: str, title_hint: str, content: str, src_type: str = "brief_text"
        ) -> None:
            path = sources_dir / filename
            path.write_text(content)
            session.add(
                ProjectSource(
                    project_id=project.id,
                    type=src_type,
                    raw_input=title_hint,
                    normalized_text=content,
                )
            )

        _write_and_register("one_pager.md", "Pullman v3 one-pager", ONE_PAGER)
        _write_and_register(
            "engineering_memo.md", "Engineering memo (numbers)", ENG_MEMO
        )
        _write_and_register(
            "customer_research.md",
            "Customer interview summary",
            CUSTOMER_RESEARCH,
        )
        _write_and_register("launch_plan.md", "Launch day plan", LAUNCH_PLAN)

        session.add(
            ProjectSource(
                project_id=project.id,
                type="url",
                raw_input=SOURCE_URL,
            )
        )

        session.commit()

        print("[seed] created demo workspace:")
        print(f"  workspace   slug={workspace.slug}  id={workspace.id}")
        print(f"  brand-kit   v1 with {len(BRAND_BANNED_PHRASES)} banned phrases")
        print(f"  competitors {', '.join(c[0] for c in COMPETITORS)}")
        print(f"  project     '{project.name}' (launch {launch.isoformat()})")
        print(f"  sources     5 (4 docs + 1 url) written to {sources_dir}")
        print()
        print(f"  open /w/{DEMO_SLUG}/projects/{project.id} to demo the run.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
