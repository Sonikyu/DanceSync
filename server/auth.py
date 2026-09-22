"""Shared-passphrase access control. With `config.PASSPHRASE` set, every API
request needs the session cookie that `POST /api/session` hands out. The
cookie, not the passphrase, rides along on `<video>` range requests.

The built web app itself stays public: it holds no media or data, and it has
to load to show the sign-in screen.
"""

from __future__ import annotations

import hashlib
import hmac

from fastapi import Request
from fastapi.responses import JSONResponse

from server import config

SESSION_COOKIE = "dancesync_session"

# Reachable before signing in: the sign-in endpoint itself.
OPEN_PATHS = {"/api/session"}
# FastAPI's generated docs describe every endpoint; keep them behind sign-in.
DOCS_PATHS = {"/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"}


def session_token(passphrase: str) -> str:
    """The cookie value. Derived from the passphrase, so changing the
    passphrase signs everyone out and there's no session state to store."""
    return hmac.new(passphrase.encode(), b"dancesync-session", hashlib.sha256).hexdigest()


def passphrase_matches(attempt: str) -> bool:
    return hmac.compare_digest(attempt.encode(), config.PASSPHRASE.encode())


def is_signed_in(request: Request) -> bool:
    if config.PASSPHRASE is None:
        return True
    cookie = request.cookies.get(SESSION_COOKIE, "")
    return hmac.compare_digest(cookie, session_token(config.PASSPHRASE))


def needs_sign_in(path: str) -> bool:
    if path in OPEN_PATHS:
        return False
    return path.startswith("/api/") or path in DOCS_PATHS


async def require_sign_in(request: Request, call_next):
    """HTTP middleware: 401 for a protected path without a valid cookie."""
    if needs_sign_in(request.url.path) and not is_signed_in(request):
        return JSONResponse({"detail": "sign in first"}, status_code=401)
    return await call_next(request)
