import asyncio
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sql_database import AsyncSessionLocal, engine
from models.sql_models import DSCRParameter
from ingest.dscr_config import DSCR_GUIDELINES
from sqlalchemy import select, text

async def ensure_columns():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE dscr_parameters ADD investor_id NVARCHAR(36) NULL"))
            print("✅ Added investor_id column to dscr_parameters table")
        except Exception:
            pass

async def seed_params():
    await ensure_columns()
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        result = await db.execute(select(DSCRParameter))
        if result.scalars().first():
            print("DSCR Parameters already exist in database. Skipping seed.")
            return

        print(f"Seeding {len(DSCR_GUIDELINES)} DSCR Parameters...")
        for param in DSCR_GUIDELINES:
            db_param = DSCRParameter(
                parameter=param["parameter"],
                category=param["category"],
                subcategory=param["subcategory"],
                ppe_field=param["ppe_field"]
            )
            db.add(db_param)
        
        await db.commit()
        print("✅ Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_params())
