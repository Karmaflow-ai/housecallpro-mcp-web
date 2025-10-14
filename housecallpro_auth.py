"""Simple per-request authentication helpers for Housecall Pro MCP."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier

_ENV_FALLBACK_KEY = "HOUSECALL_PRO_API_KEY"
_DEFAULT_SCOPE = "housecallpro"


@dataclass(frozen=True)
class AuthConfig:
    """Runtime authentication configuration."""

    fallback_api_key: str | None = None
    required_scopes: List[str] | None = None


_config: AuthConfig = AuthConfig()


def configure_auth(*, fallback_api_key: str | None, required_scopes: Iterable[str] | None = None) -> None:
    scopes = list(dict.fromkeys(required_scopes or [])) or None
    global _config
    _config = AuthConfig(fallback_api_key=fallback_api_key, required_scopes=scopes)


class PassthroughTokenVerifier(TokenVerifier):
    """Accepts any non-empty bearer token and exposes it as the API key."""

    def __init__(self, required_scopes: Iterable[str] | None = None) -> None:
        scopes = list(dict.fromkeys(required_scopes or []))
        self._scopes = scopes or [_DEFAULT_SCOPE]

    async def verify_token(self, token: str) -> AccessToken | None:
        token = (token or "").strip()
        if not token:
            return None
        return AccessToken(token=token, client_id="housecallpro-client", scopes=self._scopes)


def require_api_key() -> str:
    """Return the Housecall Pro API key for the current request."""
    access = get_access_token()
    if access and access.token:
        token = access.token.strip()
        if token:
            return token

    fallback = _config.fallback_api_key or os.getenv(_ENV_FALLBACK_KEY, "").strip()
    if fallback:
        return fallback

    raise RuntimeError(
        "Housecall Pro API key not provided. Supply an Authorization header or set HOUSECALL_PRO_API_KEY."
    )


def build_authorization_headers() -> dict[str, str]:
    api_key = require_api_key()
    return {
        "Authorization": f"Token {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


__all__ = [
    "PassthroughTokenVerifier",
    "configure_auth",
    "require_api_key",
    "build_authorization_headers",
]
