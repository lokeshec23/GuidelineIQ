# backend/migration_seed_default_prompts.py

"""
One-time migration script to seed the database with default prompts.
Run this script once before deploying the updated code.

Usage:
    python migration_seed_default_prompts.py
"""

import asyncio
from sqlalchemy.future import select
from sql_database import engine, AsyncSessionLocal, init_db
from models.sql_models import DefaultPrompts
from config import (
    DEFAULT_INGEST_PROMPT_USER_OPENAI,
    DEFAULT_INGEST_PROMPT_SYSTEM_OPENAI,
    DEFAULT_INGEST_PROMPT_USER_GEMINI,
    DEFAULT_INGEST_PROMPT_SYSTEM_GEMINI,
    DEFAULT_COMPARISON_PROMPT_USER_OPENAI,
    DEFAULT_COMPARISON_PROMPT_SYSTEM_OPENAI,
    DEFAULT_COMPARISON_PROMPT_USER_GEMINI,
    DEFAULT_COMPARISON_PROMPT_SYSTEM_GEMINI,
)


async def seed_default_prompts():
    """Seed the database with default prompts from config.py"""
    
    # Ensure database is initialized
    await init_db()
    
    print("=" * 60)
    print("SEEDING DEFAULT PROMPTS TO SQL DATABASE")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if defaults exist
            result = await session.execute(
                select(DefaultPrompts).where(DefaultPrompts.id == "system_defaults")
            )
            existing_defaults = result.scalars().first()
            
            # Prepare data
            ingest_prompts_data = {
                "openai": {
                    "system_prompt": DEFAULT_INGEST_PROMPT_SYSTEM_OPENAI,
                    "user_prompt": DEFAULT_INGEST_PROMPT_USER_OPENAI,
                },
                "gemini": {
                    "system_prompt": DEFAULT_INGEST_PROMPT_SYSTEM_GEMINI,
                    "user_prompt": DEFAULT_INGEST_PROMPT_USER_GEMINI,
                },
            }
            
            compare_prompts_data = {
                "openai": {
                    "system_prompt": DEFAULT_COMPARISON_PROMPT_SYSTEM_OPENAI,
                    "user_prompt": DEFAULT_COMPARISON_PROMPT_USER_OPENAI,
                },
                "gemini": {
                    "system_prompt": DEFAULT_COMPARISON_PROMPT_SYSTEM_GEMINI,
                    "user_prompt": DEFAULT_COMPARISON_PROMPT_USER_GEMINI,
                },
            }

            if existing_defaults:
                print("ℹ️  Default prompts record found. Updating...")
                existing_defaults.ingest_prompts = ingest_prompts_data
                existing_defaults.compare_prompts = compare_prompts_data
            else:
                print("ℹ️  Creating new default prompts record...")
                new_defaults = DefaultPrompts(
                    id="system_defaults",
                    ingest_prompts=ingest_prompts_data,
                    compare_prompts=compare_prompts_data
                )
                session.add(new_defaults)
            
            await session.commit()
            print("✅ Default prompts saved successfully")
            
            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"Document ID: system_defaults")
            print(f"Ingest Prompts: OpenAI ✓, Gemini ✓")
            print(f"Compare Prompts: OpenAI ✓, Gemini ✓")
            print("=" * 60)
            print("\n✅ Migration completed successfully!")
            return True

        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to seed default prompts: {e}")
            return False
        finally:
            await session.close()


if __name__ == "__main__":
    success = asyncio.run(seed_default_prompts())
    exit(0 if success else 1)
