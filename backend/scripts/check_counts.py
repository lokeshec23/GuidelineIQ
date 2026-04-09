
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from sqlalchemy import select, func
from sql_database import AsyncSessionLocal
from models.sql_models import DSCRParameter, Investor

async def check_counts():
    async with AsyncSessionLocal() as session:
        # Total parameters
        total_params = await session.execute(select(func.count()).select_from(DSCRParameter))
        total_params = total_params.scalar()
        print(f"Total DSCRParameters: {total_params}")

        # Parameters per investor
        investors = await session.execute(select(Investor))
        investors = investors.scalars().all()
        
        for inv in investors:
            count = await session.execute(select(func.count()).select_from(DSCRParameter).where(DSCRParameter.investor_id == inv.id))
            print(f"Investor '{inv.name}' (ID: {inv.id}): {count.scalar()} parameters")
        
        # General parameters
        general_count = await session.execute(select(func.count()).select_from(DSCRParameter).where(DSCRParameter.investor_id == None))
        print(f"General Parameters (investor_id IS NULL): {general_count.scalar()}")

if __name__ == "__main__":
    asyncio.run(check_counts())
