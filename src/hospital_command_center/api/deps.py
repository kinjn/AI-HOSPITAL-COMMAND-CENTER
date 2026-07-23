"""Dependency injection: DB session, services, graph runner."""

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.core.config import Settings, get_settings
from hospital_command_center.db.session import get_db_session
from hospital_command_center.services.workflow_service import WorkflowService


def settings_dep() -> Settings:
    return get_settings()


async def db_session_dep() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def workflow_service_dep() -> WorkflowService:
    return WorkflowService()


async def verify_api_key(x_api_key: str = Header(...)) -> None:
    settings = get_settings()
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

