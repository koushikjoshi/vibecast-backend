from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> UUID:
    return uuid4()


class Role(str, Enum):
    owner = "owner"
    approver = "approver"
    operator = "operator"
    viewer = "viewer"


class BrandPreset(str, Enum):
    playful = "playful"
    professional = "professional"
    authoritative = "authoritative"
    technical = "technical"
    blend = "blend"


class ProjectState(str, Enum):
    intake = "intake"
    planning = "planning"
    plan_ready = "plan_ready"
    producing = "producing"
    reviewing = "reviewing"
    shipped = "shipped"
    archived = "archived"


class ArtifactState(str, Enum):
    drafting = "drafting"
    awaiting_approval = "awaiting_approval"
    changes_requested = "changes_requested"
    approved = "approved"
    shipped = "shipped"
    rejected = "rejected"
    failed = "failed"


class ArtifactStudio(str, Enum):
    content = "content"
    social = "social"
    lifecycle = "lifecycle"
    podcast = "podcast"


class ArtifactType(str, Enum):
    # Content Studio
    blog = "blog"
    press_release = "press_release"
    release_notes = "release_notes"
    seo_cluster = "seo_cluster"
    landing_copy = "landing_copy"
    # Social Studio
    x_thread = "x_thread"
    linkedin_company = "linkedin_company"
    linkedin_founder = "linkedin_founder"
    hn_show = "hn_show"
    product_hunt = "product_hunt"
    reddit = "reddit"
    instagram = "instagram"
    visual_brief = "visual_brief"
    # Lifecycle Studio
    customer_email = "customer_email"
    prospect_email = "prospect_email"
    investor_email = "investor_email"
    all_hands_digest = "all_hands_digest"
    sales_deck_slide = "sales_deck_slide"
    battle_card = "battle_card"
    sdr_enablement = "sdr_enablement"
    cs_briefing = "cs_briefing"
    # Podcast Studio
    podcast_episode = "podcast_episode"


class RunPhase(str, Enum):
    planning = "planning"
    producing = "producing"
    reruns = "reruns"


class RunStatus(str, Enum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    partial = "partial"


class StepStatus(str, Enum):
    running = "running"
    ok = "ok"
    warn = "warn"
    error = "error"


class BrandVerdict(str, Enum):
    pass_ = "pass"
    warn = "warn"
    block = "block"


class ApprovalDecision(str, Enum):
    approved = "approved"
    changes_requested = "changes_requested"
    rejected = "rejected"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str | None = None
    created_at: datetime = Field(default_factory=_now)


class Workspace(SQLModel, table=True):
    __tablename__ = "workspaces"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    slug: str = Field(index=True, unique=True)
    name: str
    brand_preset: str = BrandPreset.professional.value
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=_now)


class Membership(SQLModel, table=True):
    __tablename__ = "memberships"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    role: str = Role.operator.value
    created_at: datetime = Field(default_factory=_now)


class MagicLink(SQLModel, table=True):
    __tablename__ = "magic_links"

    token: str = Field(primary_key=True)
    email: str = Field(index=True)
    workspace_invite_id: UUID | None = None
    expires_at: datetime
    used_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class Invite(SQLModel, table=True):
    __tablename__ = "invites"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    email: str
    role: str = Role.operator.value
    created_by: UUID = Field(foreign_key="users.id")
    accepted_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class BrandKit(SQLModel, table=True):
    __tablename__ = "brand_kits"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    version: int = 1
    preset: str = BrandPreset.professional.value
    tone_json: str = "{}"
    banned_phrases_json: str = "[]"
    required_disclaimers_json: str = "[]"
    competitor_policy: str = "name-only"
    pronunciation_json: str = "[]"
    legal_footer: str = ""
    positioning: str = ""
    target_icp: str = ""
    voice_samples_json: str = "[]"
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=_now)


class Competitor(SQLModel, table=True):
    __tablename__ = "competitors"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    name: str
    website_url: str
    pricing_url: str | None = None
    changelog_url: str | None = None
    positioning_cached: str | None = None
    research_json_cached: str | None = None
    last_fetched_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class MarketingProject(SQLModel, table=True):
    __tablename__ = "marketing_projects"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    slug: str = Field(index=True)
    name: str
    launch_date: date | None = None
    target_competitor_id: UUID | None = Field(default=None, foreign_key="competitors.id")
    audience_override: str | None = None
    state: str = ProjectState.intake.value
    source_dir_path: str = ""
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=_now)


class ProjectSource(SQLModel, table=True):
    __tablename__ = "project_sources"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    project_id: UUID = Field(foreign_key="marketing_projects.id", index=True)
    type: str
    raw_input: str = ""
    storage_path: str | None = None
    normalized_text: str | None = None
    metadata_json: str | None = None
    created_at: datetime = Field(default_factory=_now)


class CampaignPlan(SQLModel, table=True):
    __tablename__ = "campaign_plans"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    project_id: UUID = Field(foreign_key="marketing_projects.id", index=True)
    version: int = 1
    positioning: str = ""
    pillars_json: str = "[]"
    audience_refinement: str = ""
    channel_selection_json: str = "[]"
    competitor_angle: str = ""
    urgency_framing: str = ""
    approved_by: UUID | None = Field(default=None, foreign_key="users.id")
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class Artifact(SQLModel, table=True):
    __tablename__ = "artifacts"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    project_id: UUID = Field(foreign_key="marketing_projects.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    studio: str
    type: str
    state: str = ArtifactState.drafting.value
    title: str = ""
    content_json: str = "{}"
    brand_check_summary_json: str = "{}"
    citations_json: str | None = None
    shipped_destinations_json: str | None = None
    approved_by: UUID | None = Field(default=None, foreign_key="users.id")
    approved_at: datetime | None = None
    shipped_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class ArtifactApproval(SQLModel, table=True):
    __tablename__ = "artifact_approvals"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifacts.id", index=True)
    actor_id: UUID = Field(foreign_key="users.id")
    decision: str
    comment: str | None = None
    created_at: datetime = Field(default_factory=_now)


class Run(SQLModel, table=True):
    __tablename__ = "runs"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: UUID = Field(foreign_key="marketing_projects.id", index=True)
    phase: str = RunPhase.planning.value
    status: str = RunStatus.running.value
    started_at: datetime = Field(default_factory=_now)
    ended_at: datetime | None = None
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    error: str | None = None


class Step(SQLModel, table=True):
    __tablename__ = "steps"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", index=True)
    parent_step_id: UUID | None = None
    agent: str
    tool: str | None = None
    status: str = StepStatus.running.value
    input_json: str | None = None
    output_json: str | None = None
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
    started_at: datetime = Field(default_factory=_now)
    ended_at: datetime | None = None


class BrandCheckDecision(SQLModel, table=True):
    __tablename__ = "brand_check_decisions"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", index=True)
    step_id: UUID | None = Field(default=None, foreign_key="steps.id")
    artifact_id: UUID | None = Field(default=None, foreign_key="artifacts.id", index=True)
    section_ref: str = ""
    verdict: str
    rule: str
    note: str
    suggested_rewrite: str | None = None
    applied: bool = False
    created_at: datetime = Field(default_factory=_now)


class UsageLedger(SQLModel, table=True):
    __tablename__ = "usage_ledger"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    run_id: UUID = Field(foreign_key="runs.id", index=True)
    project_id: UUID | None = Field(default=None, foreign_key="marketing_projects.id")
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    audio_minutes: float = 0.0
    billable: bool = True
    created_at: datetime = Field(default_factory=_now)


class Host(SQLModel, table=True):
    __tablename__ = "hosts"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    name: str
    tagline: str | None = None
    bio: str = ""
    positions_json: str = "[]"
    voice_provider: str = "elevenlabs"
    voice_id: str = ""
    beliefs_md: str = ""
    approved_by: UUID | None = Field(default=None, foreign_key="users.id")
    retired_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class Show(SQLModel, table=True):
    __tablename__ = "shows"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    slug: str = Field(index=True)
    name: str
    description: str | None = None
    default_format: str = "debate"
    default_length_min: int = 6
    default_cast_json: str = "[]"
    cover_template_json: str | None = None
    visibility: str = "public"
    created_at: datetime = Field(default_factory=_now)


class Episode(SQLModel, table=True):
    __tablename__ = "episodes"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    show_id: UUID = Field(foreign_key="shows.id", index=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    artifact_id: UUID = Field(foreign_key="artifacts.id")
    slug: str
    title: str
    duration_sec: int | None = None
    audio_url: str | None = None
    transcript_json: str | None = None
    cover_art_url: str | None = None
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)


class WebhookTarget(SQLModel, table=True):
    __tablename__ = "webhook_targets"

    id: UUID = Field(default_factory=_new_id, primary_key=True)
    workspace_id: UUID = Field(foreign_key="workspaces.id", index=True)
    artifact_type: str
    target_url: str
    secret: str | None = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=_now)
