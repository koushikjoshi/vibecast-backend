from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel, HttpUrl
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db import get_session
from app.deps import (
    CurrentWorkspace,
    get_current_user,
    get_current_workspace,
    require_operator_or_above,
)
from app.models import (
    MarketingProject,
    ProjectSource,
    ProjectState,
    User,
)

logger = logging.getLogger("vibecast.projects")

router = APIRouter(prefix="/w/{slug}/projects", tags=["projects"])

_SLUG_RE = re.compile(r"[^a-z0-9-]+")
_MAX_FILE_BYTES = 20 * 1024 * 1024
_ACCEPTED_MIME = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/html",
    "image/png",
    "image/jpeg",
    "image/webp",
}


def _slugify(value: str) -> str:
    slug = value.lower().strip().replace(" ", "-")
    slug = _SLUG_RE.sub("", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "project"


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text()
                if text:
                    parts.append(text)
            except Exception:  # noqa: BLE001
                continue
        return "\n".join(parts)
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdf extract failed for %s: %s", path, exc)
        return ""


class ProjectSummaryOut(BaseModel):
    id: UUID
    slug: str
    name: str
    launch_date: date | None
    state: str
    target_competitor_id: UUID | None
    created_at: datetime


class ProjectSourceOut(BaseModel):
    id: UUID
    type: str
    raw_input: str
    storage_path: str | None
    has_normalized_text: bool
    metadata: dict[str, Any] | None
    created_at: datetime


class ProjectDetailOut(ProjectSummaryOut):
    sources: list[ProjectSourceOut]


def _serialize_project(p: MarketingProject) -> ProjectSummaryOut:
    return ProjectSummaryOut(
        id=p.id,
        slug=p.slug,
        name=p.name,
        launch_date=p.launch_date,
        state=p.state,
        target_competitor_id=p.target_competitor_id,
        created_at=p.created_at,
    )


def _serialize_source(s: ProjectSource) -> ProjectSourceOut:
    metadata = None
    if s.metadata_json:
        try:
            metadata = json.loads(s.metadata_json)
        except json.JSONDecodeError:
            metadata = None
    return ProjectSourceOut(
        id=s.id,
        type=s.type,
        raw_input=s.raw_input,
        storage_path=s.storage_path,
        has_normalized_text=bool(s.normalized_text),
        metadata=metadata,
        created_at=s.created_at,
    )


@router.get("", response_model=list[ProjectSummaryOut])
def list_projects(
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> list[ProjectSummaryOut]:
    rows = session.exec(
        select(MarketingProject)
        .where(MarketingProject.workspace_id == ws.id)
        .order_by(MarketingProject.created_at.desc())
    ).all()
    return [_serialize_project(p) for p in rows]


@router.post("", response_model=ProjectDetailOut, status_code=201)
async def create_project(
    name: Annotated[str, Form(min_length=1, max_length=120)],
    launch_date: Annotated[str | None, Form()] = None,
    target_competitor_id: Annotated[str | None, Form()] = None,
    brief_text: Annotated[str | None, Form()] = None,
    urls: Annotated[str | None, Form()] = None,
    files: Annotated[list[UploadFile] | None, File()] = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    ws: CurrentWorkspace = Depends(require_operator_or_above),
    settings: Settings = Depends(get_settings),
) -> ProjectDetailOut:
    parsed_date: date | None = None
    if launch_date:
        try:
            parsed_date = date.fromisoformat(launch_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="launch_date must be YYYY-MM-DD")

    target_uuid: UUID | None = None
    if target_competitor_id:
        try:
            target_uuid = UUID(target_competitor_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="target_competitor_id must be UUID")

    base_slug = _slugify(name)
    existing = session.exec(
        select(MarketingProject).where(
            MarketingProject.workspace_id == ws.id,
            MarketingProject.slug == base_slug,
        )
    ).first()
    suffix = 2
    slug_candidate = base_slug
    while existing is not None:
        slug_candidate = f"{base_slug}-{suffix}"
        suffix += 1
        existing = session.exec(
            select(MarketingProject).where(
                MarketingProject.workspace_id == ws.id,
                MarketingProject.slug == slug_candidate,
            )
        ).first()

    project = MarketingProject(
        workspace_id=ws.id,
        slug=slug_candidate,
        name=name.strip(),
        launch_date=parsed_date,
        target_competitor_id=target_uuid,
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

    sources: list[ProjectSource] = []

    if brief_text and brief_text.strip():
        sources.append(
            ProjectSource(
                project_id=project.id,
                type="brief_text",
                raw_input="",
                normalized_text=brief_text.strip(),
            )
        )

    if urls:
        for raw in urls.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            sources.append(
                ProjectSource(
                    project_id=project.id,
                    type="url",
                    raw_input=raw,
                )
            )

    if files:
        for upload in files:
            if not upload or upload.filename is None:
                continue
            content_type = upload.content_type or ""
            if content_type and content_type not in _ACCEPTED_MIME and not content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail=f"unsupported content type '{content_type}' for {upload.filename}",
                )

            data = await upload.read()
            if len(data) > _MAX_FILE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"{upload.filename} exceeds 20 MB limit",
                )

            safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", upload.filename)
            dest = sources_dir / safe_name
            dest.write_bytes(data)

            normalized = None
            if content_type == "application/pdf" or safe_name.lower().endswith(".pdf"):
                normalized = _extract_pdf_text(dest)
            elif content_type.startswith("text/"):
                try:
                    normalized = data.decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    normalized = None

            metadata = {
                "original_filename": upload.filename,
                "content_type": content_type,
                "size_bytes": len(data),
            }
            sources.append(
                ProjectSource(
                    project_id=project.id,
                    type="pdf" if (content_type == "application/pdf" or safe_name.lower().endswith(".pdf")) else "file",
                    raw_input=upload.filename,
                    storage_path=str(dest),
                    normalized_text=normalized,
                    metadata_json=json.dumps(metadata),
                )
            )

    if not sources:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: brief_text, urls, or files",
        )

    for s in sources:
        session.add(s)

    session.add(project)
    session.commit()
    session.refresh(project)

    rows = session.exec(
        select(ProjectSource)
        .where(ProjectSource.project_id == project.id)
        .order_by(ProjectSource.created_at)
    ).all()

    summary = _serialize_project(project)
    return ProjectDetailOut(
        **summary.model_dump(),
        sources=[_serialize_source(s) for s in rows],
    )


@router.get("/{project_id}", response_model=ProjectDetailOut)
def get_project(
    project_id: UUID,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(get_current_workspace),
) -> ProjectDetailOut:
    p = session.get(MarketingProject, project_id)
    if p is None or p.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="project not found")

    rows = session.exec(
        select(ProjectSource)
        .where(ProjectSource.project_id == p.id)
        .order_by(ProjectSource.created_at)
    ).all()

    summary = _serialize_project(p)
    return ProjectDetailOut(
        **summary.model_dump(),
        sources=[_serialize_source(s) for s in rows],
    )


class AddUrlIn(BaseModel):
    url: HttpUrl


@router.post("/{project_id}/sources/url", response_model=ProjectSourceOut, status_code=201)
def add_url_source(
    project_id: UUID,
    body: AddUrlIn,
    session: Session = Depends(get_session),
    ws: CurrentWorkspace = Depends(require_operator_or_above),
) -> ProjectSourceOut:
    p = session.get(MarketingProject, project_id)
    if p is None or p.workspace_id != ws.id:
        raise HTTPException(status_code=404, detail="project not found")
    src = ProjectSource(project_id=p.id, type="url", raw_input=str(body.url))
    session.add(src)
    session.commit()
    session.refresh(src)
    return _serialize_source(src)
