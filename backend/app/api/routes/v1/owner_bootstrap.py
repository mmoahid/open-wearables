import hashlib
import logging
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, status

from app.config import settings
from app.database import DbSession
from app.schemas.model_crud.credentials import InvitationCodeRedeemResponse
from app.services.refresh_token_service import refresh_token_service
from app.services.sdk_token_service import create_sdk_user_token
from app.services.user_service import user_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _configured_bootstrap_token_hash() -> str | None:
    configured = settings.owner_bootstrap_token_sha256
    if configured is None:
        return None

    value = (
        configured.get_secret_value()
        if hasattr(configured, "get_secret_value")
        else str(configured)
    ).strip().lower()
    return value or None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/owner/bootstrap", include_in_schema=False)
def bootstrap_owner_session(
    db: DbSession,
    x_mo_health_bootstrap_token: Annotated[
        str | None,
        Header(alias="X-Mo-Health-Bootstrap-Token"),
    ] = None,
) -> InvitationCodeRedeemResponse:
    """Issue SDK tokens for the configured single-owner mobile app.

    This endpoint is for Mo's private hosted deployment only. It replaces
    repeated one-time invitation code entry with a deployment-controlled
    bootstrap secret whose SHA-256 hash is stored in provider env vars.
    """
    expected_hash = _configured_bootstrap_token_hash()
    if not settings.owner_bootstrap_enabled or settings.owner_bootstrap_user_id is None or expected_hash is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner bootstrap is not available")

    if not x_mo_health_bootstrap_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bootstrap token is required")

    received_hash = _token_hash(x_mo_health_bootstrap_token)
    if not secrets.compare_digest(received_hash, expected_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bootstrap token")

    try:
        user_id = UUID(settings.owner_bootstrap_user_id)
    except ValueError:
        logger.error("OWNER_BOOTSTRAP_USER_ID is not a valid UUID")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Owner bootstrap is misconfigured",
        )

    user_service.get(db, user_id, raise_404=True)

    access_token = create_sdk_user_token(
        app_id=settings.owner_bootstrap_app_id,
        user_id=str(user_id),
    )
    refresh_token = refresh_token_service.create_sdk_refresh_token(
        db,
        user_id=user_id,
        app_id=settings.owner_bootstrap_app_id,
    )

    logger.info("Owner bootstrap issued SDK credentials for configured user")

    return InvitationCodeRedeemResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=user_id,
    )
