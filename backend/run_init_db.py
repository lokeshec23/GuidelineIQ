
import asyncio
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sql_database import init_db

async def run():
    await init_db()

if __name__ == "__main__":
    asyncio.run(run())
