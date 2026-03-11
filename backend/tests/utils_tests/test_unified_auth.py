"""Tests for unified authentication dependency and enforce_user_access."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.sdk_token_service import create_sdk_user_token
from app.utils.auth import enforce_user_access, get_unified_auth
from app.utils.security import create_access_token
from tests.factories import ApiKeyFactory, DeveloperFactory


class TestGetUnifiedAuth:
    """Tests for get_unified_auth dependency."""

    @pytest.mark.asyncio
    async def test_developer_token_returns_developer_context(self, db: Session) -> None:
        """Developer JWT should return AuthContext with auth_type='developer'."""
        developer = DeveloperFactory()
        token = create_access_token(subject=str(developer.id))

        result = await get_unified_auth(db=db, token=token, x_open_wearables_api_key=None)

        assert result.auth_type == "developer"
        assert result.developer_id == developer.id

    @pytest.mark.asyncio
    async def test_sdk_token_returns_sdk_context(self, db: Session) -> None:
        """SDK token should return AuthContext with auth_type='sdk_token'."""
        user_id = str(uuid4())
        token = create_sdk_user_token("test_app", user_id)

        result = await get_unified_auth(db=db, token=token, x_open_wearables_api_key=None)

        assert result.auth_type == "sdk_token"
        assert str(result.user_id) == user_id
        assert result.app_id == "test_app"

    @pytest.mark.asyncio
    async def test_api_key_returns_api_key_context(self, db: Session) -> None:
        """API key should return AuthContext with auth_type='api_key'."""
        api_key = ApiKeyFactory()

        result = await get_unified_auth(db=db, token=None, x_open_wearables_api_key=api_key.id)

        assert result.auth_type == "api_key"
        assert result.api_key_id == api_key.id

    @pytest.mark.asyncio
    async def test_developer_token_preferred_over_api_key(self, db: Session) -> None:
        """When both developer token and API key are provided, developer token wins."""
        developer = DeveloperFactory()
        api_key = ApiKeyFactory()
        token = create_access_token(subject=str(developer.id))

        result = await get_unified_auth(db=db, token=token, x_open_wearables_api_key=api_key.id)

        assert result.auth_type == "developer"
        assert result.developer_id == developer.id

    @pytest.mark.asyncio
    async def test_sdk_token_preferred_over_api_key(self, db: Session) -> None:
        """When both SDK token and API key are provided, SDK token wins."""
        api_key = ApiKeyFactory()
        user_id = str(uuid4())
        token = create_sdk_user_token("test_app", user_id)

        result = await get_unified_auth(db=db, token=token, x_open_wearables_api_key=api_key.id)

        assert result.auth_type == "sdk_token"
        assert str(result.user_id) == user_id

    @pytest.mark.asyncio
    async def test_no_auth_raises_401(self, db: Session) -> None:
        """Missing auth should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_unified_auth(db=db, token=None, x_open_wearables_api_key=None)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_token_falls_back_to_api_key(self, db: Session) -> None:
        """Invalid JWT should fall through to API key."""
        api_key = ApiKeyFactory()

        result = await get_unified_auth(db=db, token="invalid.jwt.token", x_open_wearables_api_key=api_key.id)

        assert result.auth_type == "api_key"
        assert result.api_key_id == api_key.id

    @pytest.mark.asyncio
    async def test_invalid_token_and_no_api_key_raises_401(self, db: Session) -> None:
        """Invalid JWT and no API key should raise 401."""
        with pytest.raises(HTTPException) as exc_info:
            await get_unified_auth(db=db, token="invalid.jwt.token", x_open_wearables_api_key=None)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_nonexistent_developer_falls_back_to_api_key(self, db: Session) -> None:
        """Token with non-existent developer ID should fall through to API key."""
        api_key = ApiKeyFactory()
        token = create_access_token(subject=str(uuid4()))

        result = await get_unified_auth(db=db, token=token, x_open_wearables_api_key=api_key.id)

        assert result.auth_type == "api_key"


class TestEnforceUserAccess:
    """Tests for enforce_user_access helper."""

    def test_sdk_token_matching_user_passes(self) -> None:
        """SDK token with matching user_id should not raise."""
        from app.schemas.sdk import AuthContext

        user_id = uuid4()
        auth = AuthContext(auth_type="sdk_token", user_id=user_id, app_id="test_app")

        # Should not raise
        enforce_user_access(auth, user_id)

    def test_sdk_token_mismatched_user_raises_403(self) -> None:
        """SDK token with different user_id should raise 403."""
        from app.schemas.sdk import AuthContext

        auth = AuthContext(auth_type="sdk_token", user_id=uuid4(), app_id="test_app")

        with pytest.raises(HTTPException) as exc_info:
            enforce_user_access(auth, uuid4())

        assert exc_info.value.status_code == 403

    def test_sdk_token_without_user_id_raises_403(self) -> None:
        """SDK token without user_id should raise 403."""
        from app.schemas.sdk import AuthContext

        auth = AuthContext(auth_type="sdk_token", app_id="test_app")

        with pytest.raises(HTTPException) as exc_info:
            enforce_user_access(auth, uuid4())

        assert exc_info.value.status_code == 403

    def test_developer_auth_allows_any_user(self) -> None:
        """Developer auth should allow access to any user's data."""
        from app.schemas.sdk import AuthContext

        auth = AuthContext(auth_type="developer", developer_id=uuid4())

        # Should not raise for any user_id
        enforce_user_access(auth, uuid4())

    def test_api_key_auth_allows_any_user(self) -> None:
        """API key auth should allow access to any user's data."""
        from app.schemas.sdk import AuthContext

        auth = AuthContext(auth_type="api_key", api_key_id="sk-test123")

        # Should not raise for any user_id
        enforce_user_access(auth, uuid4())
