import asyncio
import logging
from sql_database import init_db

async def test_init():
    logging.basicConfig(level=logging.INFO)
    try:
        await init_db()
        print("Success!")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_init())
