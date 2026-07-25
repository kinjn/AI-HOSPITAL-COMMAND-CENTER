"""Add the `tracking_id` column to an existing `encounters` table.

`scripts/init_db.py` uses `Base.metadata.create_all`, which only creates
missing *tables* — it won't add a new column to a table that already
exists. Anyone with a pre-existing `data/hospital_command_center.db` (or
other already-initialized DB) from before the Patient Portal's Tracking-ID
endpoints (api/routes/patient.py) needs to run this once. Safe to run
multiple times — it checks for the column first and does nothing if it's
already there. Fresh databases created via init_db.py after this change
already have the column and don't need this script.

Usage:
    python scripts/migrate_add_tracking_id.py
"""

import asyncio

from sqlalchemy import text

from hospital_command_center.db.session import get_engine


async def migrate() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(encounters)"))
        columns = {row[1] for row in result.fetchall()}

        if "tracking_id" in columns:
            print("tracking_id column already present — nothing to do.")
            return

        await conn.execute(text("ALTER TABLE encounters ADD COLUMN tracking_id VARCHAR(16)"))
        await conn.execute(
            text("CREATE UNIQUE INDEX IF NOT EXISTS ix_encounters_tracking_id ON encounters (tracking_id)")
        )
        print("Added tracking_id column and unique index to encounters table.")


if __name__ == "__main__":
    asyncio.run(migrate())
