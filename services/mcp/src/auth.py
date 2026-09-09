"""Authentication for the network MCP transport."""

from __future__ import annotations

import hmac

from fastmcp.server.auth import AccessToken, TokenVerifier


class ApiTokenVerifier(TokenVerifier):
    """Verify a shared bearer token without exposing the Cube secret."""

    def __init__(self, api_token: str) -> None:
        super().__init__()
        self._api_token = api_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token, self._api_token):
            return None
        return AccessToken(
            token=token,
            client_id="nba-mcp-api-token",
            scopes=[],
            subject="nba-mcp-client",
            claims={"auth_method": "api_token"},
        )
