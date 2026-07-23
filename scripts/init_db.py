"""Initialize database schema."""

import asyncio
from pathlib import Path

from hospital_command_center.core.config import get_settings
from hospital_command_center.db import models  # noqa: F401
from hospital_command_center.db.base import Base
from hospital_command_center.db.session import get_engine


async def init_db() -> None:
    settings = get_settings()
    db_path = settings.database_url.split("///")[-1]
    if db_path.startswith("./"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created.")


if __name__ == "__main__":
    asyncio.run(init_db())
