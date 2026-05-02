"""Tests for the private owner bootstrap endpoint."""

import hashlib
from unittest.mock import patch

from jose import jwt
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.config import settings
from tests.factories import UserFactory


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TestOwnerBootstrap:
    def test_disabled_returns_404(self, client: TestClient, db: Session, api_v1_prefix: str) -> None:
        response = client.post(f"{api_v1_prefix}/owner/bootstrap")

        assert response.status_code == 404

    def test_missing_token_returns_401(self, client: TestClient, db: Session, api_v1_prefix: str) -> None:
        user = UserFactory()

        with (
            patch.object(settings, "owner_bootstrap_enabled", True),
            patch.object(settings, "owner_bootstrap_user_id", str(user.id)),
            patch.object(settings, "owner_bootstrap_token_sha256", _sha256("correct-token")),
        ):
            response = client.post(f"{api_v1_prefix}/owner/bootstrap")

        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client: TestClient, db: Session, api_v1_prefix: str) -> None:
        user = UserFactory()

        with (
            patch.object(settings, "owner_bootstrap_enabled", True),
            patch.object(settings, "owner_bootstrap_user_id", str(user.id)),
            patch.object(settings, "owner_bootstrap_token_sha256", _sha256("correct-token")),
        ):
            response = client.post(
                f"{api_v1_prefix}/owner/bootstrap",
                headers={"X-Mo-Health-Bootstrap-Token": "wrong-token"},
            )

        assert response.status_code == 401

    def test_success_returns_sdk_tokens(self, client: TestClient, db: Session, api_v1_prefix: str) -> None:
        user = UserFactory()

        with (
            patch.object(settings, "owner_bootstrap_enabled", True),
            patch.object(settings, "owner_bootstrap_user_id", str(user.id)),
            patch.object(settings, "owner_bootstrap_token_sha256", _sha256("correct-token")),
            patch.object(settings, "owner_bootstrap_app_id", "owner-bootstrap:test"),
        ):
            response = client.post(
                f"{api_v1_prefix}/owner/bootstrap",
                headers={"X-Mo-Health-Bootstrap-Token": "correct-token"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(user.id)
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == settings.access_token_expire_minutes * 60
        assert data["refresh_token"].startswith("rt-")

        payload = jwt.decode(
            data["access_token"],
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": False},
        )
        assert payload["scope"] == "sdk"
        assert payload["sub"] == str(user.id)
        assert payload["app_id"] == "owner-bootstrap:test"
