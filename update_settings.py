
import asyncio
import os
from database import db_manager, init_db

async def update_admin_settings():
    await init_db()
    
    admin_user = await db_manager.users.find_one({"role": "admin"})
    if not admin_user:
        print("❌ No admin user found.")
        return

    user_id = str(admin_user["_id"])
    print(f"Found admin user: {user_id}")

    # Update settings
    result = await db_manager.user_settings.update_one(
        {"user_id": user_id},
        {"$set": {
            "default_model_provider": "openai",
            "default_model_name": "gpt-4o"
        }},
        upsert=True
    )

    if result.modified_count > 0 or result.upserted_id:
        print("✅ Successfully updated admin settings to use OpenAI (gpt-4o).")
    else:
        print("ℹ️ Settings were already set to OpenAI.")

if __name__ == "__main__":
    asyncio.run(update_admin_settings())
