
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from urllib.parse import quote_plus

# Direct configuration to avoid import issues
DB_SERVER = "localhost"
DB_PORT = "1433"
DB_USER = "sa"
DB_PASSWORD = "Loandna@2026"
DB_NAME = "guidelineiq_db"
encoded_password = quote_plus(DB_PASSWORD)
SQL_SERVER_URI = f"mssql+aioodbc://{DB_USER}:{encoded_password}@{DB_SERVER}:{DB_PORT}/{DB_NAME}?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"

engine = create_async_engine(SQL_SERVER_URI, echo=True)

async def migrate():
    print(f"🚀 Connecting to {DB_NAME}...")
    try:
        async with engine.begin() as conn:
            print("🔍 Checking if column 'upload_date' exists...")
            # Check if column exists first
            check_sql = text("SELECT col.name FROM sys.columns col JOIN sys.tables tab ON col.object_id = tab.object_id WHERE tab.name = 'files' AND col.name = 'upload_date'")
            result = await conn.execute(check_sql)
            if result.fetchone():
                print("🔄 Renaming 'upload_date' to 'created_at'...")
                await conn.execute(text("EXEC sp_rename 'files.upload_date', 'created_at', 'COLUMN'"))
                print("✅ Successfully renamed column.")
            else:
                print("ℹ️ Column 'upload_date' not found. It might already be renamed or the table doesn't exist.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate())
