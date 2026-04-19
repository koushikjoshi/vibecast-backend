from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from sqlmodel import Session, select

from app.config import get_settings
from app.models import MagicLink, User

logger = logging.getLogger("vibecast.auth")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def issue_magic_link(session: Session, email: str) -> MagicLink:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    link = MagicLink(
        token=token,
        email=email.lower().strip(),
        expires_at=_now() + timedelta(minutes=settings.magic_link_ttl_min),
    )
    session.add(link)
    session.commit()
    session.refresh(link)

    link_url = f"{settings.public_frontend_url}/auth/callback?token={token}"
    if settings.magic_link_dev_log:
        # Very visible in server logs so the operator can grab it during local/demo use.
        logger.warning("=" * 72)
        logger.warning("MAGIC LINK for %s", email)
        logger.warning("%s", link_url)
        logger.warning("=" * 72)
    return link


def consume_magic_link(session: Session, token: str) -> User | None:
    link = session.get(MagicLink, token)
    if link is None:
        return None
    if link.used_at is not None:
        return None
    link_expires = link.expires_at if link.expires_at.tzinfo else link.expires_at.replace(tzinfo=timezone.utc)
    if link_expires < _now():
        return None

    link.used_at = _now()
    session.add(link)

    user = session.exec(select(User).where(User.email == link.email)).first()
    if user is None:
        user = User(email=link.email)
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        session.commit()
    return user


def create_session_jwt(user_id: UUID) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(days=settings.session_max_age_days)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_session_jwt(token: str) -> UUID | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return UUID(sub)
    except ValueError:
        return None
