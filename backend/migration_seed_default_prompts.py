# backend/migration_seed_default_prompts.py

"""
One-time migration script to seed the database with default prompts.
Run this script once before deploying the updated code.

Usage:
    python migration_seed_default_prompts.py
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from config import (
    MONGO_URI,
    DB_NAME,
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
    
    print("=" * 60)
    print("SEEDING DEFAULT PROMPTS TO DATABASE")
    print("=" * 60)
    
    # Connect to MongoDB
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[DB_NAME]
        default_prompts_collection = db["default_prompts"]
        
        print(f"✅ Connected to MongoDB: {DB_NAME}")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return False
    
    # Prepare default prompts document
    default_prompts_doc = {
        "_id": "system_defaults",
        "ingest_prompts": {
            "openai": {
                "system_prompt": DEFAULT_INGEST_PROMPT_SYSTEM_OPENAI,
                "user_prompt": DEFAULT_INGEST_PROMPT_USER_OPENAI,
            },
            "gemini": {
                "system_prompt": DEFAULT_INGEST_PROMPT_SYSTEM_GEMINI,
                "user_prompt": DEFAULT_INGEST_PROMPT_USER_GEMINI,
            },
        },
        "compare_prompts": {
            "openai": {
                "system_prompt": DEFAULT_COMPARISON_PROMPT_SYSTEM_OPENAI,
                "user_prompt": DEFAULT_COMPARISON_PROMPT_USER_OPENAI,
            },
            "gemini": {
                "system_prompt": DEFAULT_COMPARISON_PROMPT_SYSTEM_GEMINI,
                "user_prompt": DEFAULT_COMPARISON_PROMPT_USER_GEMINI,
            },
        },
    }
    
    # Insert or update the default prompts
    try:
        result = await default_prompts_collection.replace_one(
            {"_id": "system_defaults"},
            default_prompts_doc,
            upsert=True
        )
        
        if result.upserted_id:
            print("✅ Default prompts inserted successfully")
        elif result.modified_count > 0:
            print("✅ Default prompts updated successfully")
        else:
            print("ℹ️  Default prompts already exist and are up to date")
        
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
        print(f"❌ Failed to seed default prompts: {e}")
        return False
    finally:
        client.close()


if __name__ == "__main__":
    success = asyncio.run(seed_default_prompts())
    exit(0 if success else 1)
