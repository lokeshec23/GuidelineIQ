# scripts/update_embedding_config.py
"""
Quick script to update admin settings with Azure embedding deployment configuration.
Run this to configure the embedding deployment without needing .env file.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_manager

async def update_embedding_config():
    """Update admin settings with embedding deployment configuration."""
    
    # Initialize database
    await db_manager.connect()
    
    if db_manager.users is None or db_manager.settings is None:
        print("❌ Error: Database connection failed")
        return False
    
    # Find admin user
    admin_user = await db_manager.users.find_one({"role": "admin"})
    if not admin_user:
        print("❌ Error: No admin user found")
        return False
    
    admin_id = str(admin_user["_id"])
    print(f"✅ Found admin user: {admin_user['email']}")
    
    # Update settings with embedding deployment
    update_data = {
        "openai_embedding_deployment": "embedding-model",
        "updated_at": datetime.utcnow()
    }
    
    result = await db_manager.settings.update_one(
        {"user_id": admin_id},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        print("✅ Successfully updated embedding deployment configuration!")
        print(f"   ✓ Azure Embedding Deployment: embedding-model")
        
        # Show current settings
        settings = await db_manager.settings.find_one({"user_id": admin_id})
        if settings:
            print("\n📋 Current Azure OpenAI Configuration:")
            if settings.get("openai_endpoint"):
                print(f"   ✓ Endpoint: {settings['openai_endpoint']}")
            if settings.get("openai_deployment"):
                print(f"   ✓ Chat Deployment: {settings['openai_deployment']}")
            if settings.get("openai_embedding_deployment"):
                print(f"   ✓ Embedding Deployment: {settings['openai_embedding_deployment']}")
        
        return True
    else:
        print("⚠️ No changes made (settings may already be up to date)")
        return True

if __name__ == "__main__":
    print("🔧 Updating embedding deployment configuration...\n")
    success = asyncio.run(update_embedding_config())
    sys.exit(0 if success else 1)
