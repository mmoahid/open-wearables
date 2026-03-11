from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class SDKTokenRequest(BaseModel):
    """Request schema for exchanging app credentials for user token.

    Both fields are optional - if not provided, admin authentication is required.
    """

    app_id: str | None = None
    app_secret: str | None = None


class SDKAuthContext(BaseModel):
    """Context returned by SDK authentication dependency."""

    auth_type: Literal["sdk_token", "api_key"]
    user_id: UUID | None = None  # From SDK token (sub claim)
    app_id: str | None = None  # From SDK token
    api_key_id: str | None = None  # From API key


class AuthContext(BaseModel):
    """Unified authentication context for data-access endpoints.

    Supports three auth types:
    - developer: Full access via developer JWT token
    - sdk_token: Scoped access via SDK user token (bound to user_id)
    - api_key: Full access via API key header
    """

    auth_type: Literal["developer", "sdk_token", "api_key"]
    developer_id: UUID | None = None  # From developer JWT
    user_id: UUID | None = None  # From SDK token (sub claim)
    app_id: str | None = None  # From SDK token
    api_key_id: str | None = None  # From API key
