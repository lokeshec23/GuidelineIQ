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

from sql_database import AsyncSessionLocal
from models.sql_models import User, UserSettings
from sqlalchemy.future import select

async def update_embedding_config():
    """Update admin settings with embedding deployment configuration."""
    
    async with AsyncSessionLocal() as db:
        # Find admin user
        result = await db.execute(select(User).where(User.role == "admin").limit(1))
        admin_user = result.scalars().first()
        
        if not admin_user:
            result = await db.execute(select(User).where(User.is_admin == True).limit(1))
            admin_user = result.scalars().first()
            
        if not admin_user:
            print("❌ Error: No admin user found")
            return False
        
        print(f"✅ Found admin user: {admin_user.email}")
        
        # Get settings
        result = await db.execute(select(UserSettings).where(UserSettings.user_id == admin_user.id))
        settings_record = result.scalars().first()
        
        if not settings_record:
            settings_record = UserSettings(user_id=admin_user.id, settings_json={})
            db.add(settings_record)
        
        # Update settings with embedding deployment
        settings_json = settings_record.settings_json or {}
        settings_json["openai_embedding_deployment"] = "extraction-embedding"
        settings_record.settings_json = settings_json
        settings_record.updated_at = datetime.utcnow()
        
        await db.commit()
        print("✅ Successfully updated embedding deployment configuration!")
        print(f"   ✓ Azure Embedding Deployment: extraction-embedding")
        return True

if __name__ == "__main__":
    print("🔧 Updating embedding deployment configuration...\n")
    success = asyncio.run(update_embedding_config())
    sys.exit(0 if success else 1)
