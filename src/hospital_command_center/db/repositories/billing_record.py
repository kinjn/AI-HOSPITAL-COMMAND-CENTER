"""Billing record repository — all DB operations for the billing_records table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hospital_command_center.db.models.billing_record import BillingRecordModel


class BillingRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, billing_record: BillingRecordModel) -> BillingRecordModel:
        self.session.add(billing_record)
        await self.session.commit()
        await self.session.refresh(billing_record)
        return billing_record

    async def get_by_id(self, billing_record_id: str) -> BillingRecordModel | None:
        result = await self.session.execute(
            select(BillingRecordModel).where(BillingRecordModel.id == billing_record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_encounter_id(self, encounter_id: str) -> list[BillingRecordModel]:
        result = await self.session.execute(
            select(BillingRecordModel)
            .where(BillingRecordModel.encounter_id == encounter_id)
            .order_by(BillingRecordModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[BillingRecordModel]:
        result = await self.session.execute(
            select(BillingRecordModel)
            .where(BillingRecordModel.status == status)
            .order_by(BillingRecordModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, billing_record: BillingRecordModel) -> BillingRecordModel:
        await self.session.commit()
        await self.session.refresh(billing_record)
        return billing_record

    async def delete(self, billing_record: BillingRecordModel) -> None:
        await self.session.delete(billing_record)
        await self.session.commit()