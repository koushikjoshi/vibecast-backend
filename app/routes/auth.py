from __future__ import annotations

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session

from app.auth import consume_magic_link, create_session_jwt, issue_magic_link
from app.config import Settings, get_settings
from app.db import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class MagicLinkRequest(BaseModel):
    email: EmailStr


@router.post("/magic-link", status_code=status.HTTP_204_NO_CONTENT)
def request_magic_link(
    body: MagicLinkRequest,
    session: Session = Depends(get_session),
) -> Response:
    issue_magic_link(session, body.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/magic-link/{token}")
def consume_magic_link_endpoint(
    token: str,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    user = consume_magic_link(session, token)
    if user is None:
        raise HTTPException(status_code=400, detail="invalid or expired link")
    jwt_token = create_session_jwt(user.id)

    response = RedirectResponse(
        url=f"{settings.public_frontend_url}/onboarding",
        status_code=302,
    )
    _set_session_cookie(response, jwt_token, settings)
    return response


class ConsumeBody(BaseModel):
    token: str


@router.post("/magic-link/consume")
def consume_magic_link_api(
    body: ConsumeBody,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """API-style consumption for SPAs — returns user JSON and sets the cookie."""
    user = consume_magic_link(session, body.token)
    if user is None:
        raise HTTPException(status_code=400, detail="invalid or expired link")
    jwt_token = create_session_jwt(user.id)

    response = JSONResponse(
        content={
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
        }
    )
    _set_session_cookie(response, jwt_token, settings)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    settings: Settings = Depends(get_settings),
) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        settings.session_cookie_name,
        httponly=True,
        secure=settings.env != "development",
        samesite="lax",
    )
    return response


def _set_session_cookie(response: Response, jwt_token: str, settings: Settings) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=jwt_token,
        max_age=settings.session_max_age_days * 24 * 3600,
        httponly=True,
        secure=settings.env != "development",
        samesite="lax",
        path="/",
    )
