print("Script starting...")
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys
import os

# Add current directory to path so we can import config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import SQL_SERVER_URI

async def add_username_column():
    engine = create_async_engine(SQL_SERVER_URI, echo=True)
    async with engine.begin() as conn:
        try:
            # Check if column exists
            # For SQL Server
            query = text("""
                IF NOT EXISTS (
                    SELECT * FROM sys.columns 
                    WHERE object_id = OBJECT_ID(N'[dbo].[users]') 
                    AND name = 'username'
                )
                BEGIN
                    ALTER TABLE [dbo].[users] ADD [username] NVARCHAR(255) NULL;
                    CREATE UNIQUE INDEX [ix_users_username] ON [dbo].[users] ([username]) WHERE [username] IS NOT NULL;
                END
            """)
            await conn.execute(query)
            print("Successfully added username column to users table.")
        except Exception as e:
            print(f"Error adding column: {e}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_username_column())
