"""Encounter CRUD and care pathway queries."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.api.deps import db_session_dep
from hospital_command_center.db.repositories.encounter import EncounterRepository

router = APIRouter(prefix="/encounters", tags=["encounters"])


@router.get("")
async def list_encounters(
    session: AsyncSession = Depends(db_session_dep),
) -> dict:
    repo = EncounterRepository(session)
    rows = await repo.list_all()
    return {
        "items": [
            {
                "id": r.id,
                "patient_id": r.patient_id,
                "status": r.status,
                "pathway": r.pathway,
            }
            for r in rows
        ],
        "stub": True,
    }
