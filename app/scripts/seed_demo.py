"""Seed the database with a demo workspace, brand kit, competitors, and a
pre-filled marketing project. Run via:

    python -m app.scripts.seed_demo

Idempotent: only creates rows if the demo email doesn't already exist.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from uuid import uuid4

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
DEMO_SLUG = "acme-labs"
DEMO_NAME = "Acme Labs"

DEMO_BRIEF = """
Acme Labs is shipping Copilot Workspace — an AI workspace for product and
marketing teams that lets them ship launches, docs, and campaigns in hours
instead of weeks.

Key features launching this week:
- Multi-agent orchestration (CMO + 17 specialists)
- Brand-safe content generation with immutable brand kit versioning
- Live trace of every agent decision with tokens + cost reporting
- Native integration with Linear, Notion, and Slack

Target ICP: Seed/Series-A B2B SaaS teams, ARR $1–20M, led by a founder or
first PMM hire. Primary competitors: Jasper and Typeface. Pricing: $99/mo
per workspace. Launch date: next Tuesday.
"""


def run() -> None:
    settings = get_settings()
    init_db()

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == DEMO_EMAIL)).first()
        if existing is not None:
            logger.info("demo data already present (user %s)", existing.id)
            print(
                f"[seed] demo user exists: id={existing.id} email={existing.email}. "
                "Sign in with this email in dev (magic link is logged to stdout)."
            )
            return

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

        brand = BrandKit(
            workspace_id=workspace.id,
            version=1,
            preset=BrandPreset.professional.value,
            tone_json=json.dumps(
                {"voice": "Clear, confident, evidence-first. No hype."}
            ),
            banned_phrases_json=json.dumps(
                ["revolutionary", "best-in-class", "game-changing"]
            ),
            required_disclaimers_json=json.dumps([]),
            competitor_policy="name-only",
            pronunciation_json=json.dumps([]),
            legal_footer="© 2026 Acme Labs.",
            positioning="Acme Copilot Workspace is the operating system for fast-moving B2B teams.",
            target_icp="Seed/Series-A B2B SaaS, ARR $1–20M, founder- or PMM-led marketing.",
            voice_samples_json=json.dumps([]),
            created_by=user.id,
        )
        session.add(brand)

        for name, website in [
            ("Jasper", "https://www.jasper.ai"),
            ("Typeface", "https://www.typeface.ai"),
        ]:
            session.add(
                Competitor(
                    workspace_id=workspace.id,
                    name=name,
                    website_url=website,
                )
            )

        project = MarketingProject(
            workspace_id=workspace.id,
            slug="copilot-workspace-launch",
            name="Copilot Workspace launch",
            launch_date=date.today(),
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

        session.add(
            ProjectSource(
                project_id=project.id,
                type="brief_text",
                raw_input="",
                normalized_text=DEMO_BRIEF.strip(),
            )
        )
        session.add(
            ProjectSource(
                project_id=project.id,
                type="url",
                raw_input="https://www.acmelabs.dev/changelog",
            )
        )

        session.commit()

        print("[seed] created demo data:")
        print(f"  user    id={user.id} email={user.email}")
        print(f"  workspace slug={workspace.slug} id={workspace.id}")
        print(f"  brand-kit version=1")
        print(f"  competitors: Jasper, Typeface")
        print(f"  project id={project.id} name='{project.name}'")
        print(
            "[seed] next: start the dev server, hit /auth/magic-link with this email, "
            "grab the magic link from stdout, and kick off a planning run."
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
