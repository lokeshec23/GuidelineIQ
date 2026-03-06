import asyncio
import sys
from sqlalchemy import text
from sql_database import engine

async def add_column():
    print("Adding investor_id column...")
    try:
        async with engine.begin() as conn:
            await conn.execute(text('ALTER TABLE dscr_parameters ADD investor_id NVARCHAR(36) NULL'))
            print("Successfully added investor_id column.")
    except Exception as e:
        print(f"Error adding column: {e}")

if __name__ == '__main__':
    asyncio.run(add_column())
