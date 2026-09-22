"""GET /api/session (am I signed in?) and POST /api/session (sign in)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from server import config
from server.auth import SESSION_COOKIE, is_signed_in, passphrase_matches, session_token
from server.models import SessionStatus, SignInRequest

router = APIRouter(prefix="/api/session", tags=["session"])


@router.get("", response_model=SessionStatus)
def session_status(request: Request) -> SessionStatus:
    return SessionStatus(signed_in=is_signed_in(request))


@router.post("", status_code=204)
def sign_in(body: SignInRequest, request: Request, response: Response) -> None:
    if config.PASSPHRASE is None:
        return
    if not passphrase_matches(body.passphrase):
        raise HTTPException(401, "wrong passphrase")

    response.set_cookie(
        SESSION_COOKIE,
        session_token(config.PASSPHRASE),
        max_age=config.SESSION_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        # Behind a TLS-terminating proxy this needs uvicorn's proxy headers
        # (the Docker image trusts X-Forwarded-Proto).
        secure=request.url.scheme == "https",
    )
