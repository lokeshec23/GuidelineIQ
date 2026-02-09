
import asyncio
import sys
import os

# Add the backend directory to sys.path so we can import sql_database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from sql_database import engine

async def migrate():
    print("🚀 Starting migration: Renaming 'upload_date' to 'created_at' in 'files' table...")
    try:
        async with engine.begin() as conn:
            # SQL Server syntax to rename a column
            # sp_rename 'table_name.old_column_name', 'new_column_name', 'COLUMN'
            await conn.execute(text("EXEC sp_rename 'files.upload_date', 'created_at', 'COLUMN'"))
            print("✅ Successfully renamed 'upload_date' to 'created_at' in 'files' table.")
    except Exception as e:
        if "does not exist" in str(e) or "42S22" in str(e):
            print(f"⚠️ Column 'upload_date' might not exist or already renamed. Error: {e}")
        else:
            print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
