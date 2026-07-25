"""Add insurance document request columns to an existing `billing_records` table.

`scripts/init_db.py` uses `Base.metadata.create_all`, which only creates
missing *tables* — it won't add new columns to a table that already exists.
Anyone with a pre-existing `data/hospital_command_center.db` (or other
already-initialized DB) from before the "Demand insurance document"
patient portal feature needs to run this once. Safe to run multiple
times — it checks for each column first and does nothing if it's already
there. Fresh databases created via init_db.py after this change already
have these columns and don't need this script.

Usage:
    python scripts/migrate_add_insurance_request.py
"""

import asyncio

from sqlalchemy import text

from hospital_command_center.db.session import get_engine

_NEW_COLUMNS = {
    "insurance_request_status": "VARCHAR(32)",
    "insurance_requested_at": "DATETIME",
    "insurance_responded_at": "DATETIME",
}


async def migrate() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(billing_records)"))
        existing_columns = {row[1] for row in result.fetchall()}

        added = []
        for column, ddl_type in _NEW_COLUMNS.items():
            if column in existing_columns:
                continue
            await conn.execute(text(f"ALTER TABLE billing_records ADD COLUMN {column} {ddl_type}"))
            added.append(column)

        if added:
            print(f"Added columns to billing_records: {', '.join(added)}")
        else:
            print("insurance request columns already present — nothing to do.")


if __name__ == "__main__":
    asyncio.run(migrate())
