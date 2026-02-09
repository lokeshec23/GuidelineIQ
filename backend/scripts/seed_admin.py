# scripts/seed_admin.py

import os
import sys
import asyncio
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy.future import select

# Add parent directory to path to import from backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_database import AsyncSessionLocal, init_db
from models.sql_models import User, UserSettings
from auth.utils import hash_password
from settings.models import create_or_update_settings

async def seed_admin():
    """
    Creates the admin user if it doesn't already exist in the SQL database.
    Reads credentials from environment variables and initializes admin settings.
    """
    # Ensure database and tables are initialized
    await init_db()
    
    # Load environment variables
    load_dotenv()
    
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_email or not admin_password:
        print("❌ Error: ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env file")
        return False
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if admin already exists by role
            result = await session.execute(select(User).where(User.role == "admin"))
            existing_admin = result.scalars().first()
            
            if existing_admin:
                print(f"✅ Admin user already exists: {existing_admin.email}")
                admin_id = existing_admin.id
            else:
                # Check if email is already taken by a regular user
                result = await session.execute(select(User).where(User.email == admin_email))
                email_exists = result.scalars().first()
                
                if email_exists:
                    print(f"⚠️  User with email {admin_email} exists but is not an admin. Upgrading...")
                    email_exists.role = "admin"
                    email_exists.is_admin = True
                    await session.commit()
                    admin_id = email_exists.id
                else:
                    # Create new admin user
                    new_admin = User(
                        username=admin_username,
                        email=admin_email,
                        hashed_password=hash_password(admin_password),
                        role="admin",
                        is_admin=True,
                        is_active=True
                    )
                    session.add(new_admin)
                    await session.commit()
                    await session.refresh(new_admin)
                    admin_id = new_admin.id
                    print(f"✅ Admin user created successfully!")
                    print(f"   Email: {admin_email}")
                    print(f"   ID: {admin_id}")

            # Initialize admin settings from environment variables
            print("\n🔧 Initializing admin settings from environment variables...")
            
            settings_data = {
                # API Keys
                "gemini_api_key": os.getenv("GEMINI_API_KEY"),
                "openai_api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                
                # Azure OpenAI Configuration
                "openai_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "openai_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                "openai_embedding_deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "embedding-model"),
                
                # Default Model Configuration
                "default_model_provider": os.getenv("DEFAULT_MODEL_PROVIDER", "openai"),
                "default_model_name": os.getenv("DEFAULT_MODEL_NAME", "gpt-4o"),
                
                # LLM Parameters (with defaults)
                "temperature": float(os.getenv("DEFAULT_TEMPERATURE", "0.3")),
                "max_output_tokens": int(os.getenv("DEFAULT_MAX_TOKENS", "8192")),
                "top_p": float(os.getenv("DEFAULT_TOP_P", "0.95")),
                "stop_sequences": [],
                
                # PDF Chunking
                "pages_per_chunk": int(os.getenv("DEFAULT_PAGES_PER_CHUNK", "1")),
                
                # Comparison settings
                "comparison_chunk_size": int(os.getenv("COMPARISON_CHUNK_SIZE", "10")),
                "max_comparison_chunks": int(os.getenv("MAX_COMPARISON_CHUNKS", "0"))
            }
            print("Admin Settings", settings_data)
            # Use the settings model to save to user_settings table
            await create_or_update_settings(session, admin_id, settings_data)
            print("✅ Admin settings initialized successfully!")
            
            # Print status summary
            if settings_data.get("gemini_api_key"):
                print(f"   ✓ Gemini API Key configured")
            if settings_data.get("openai_api_key"):
                print(f"   ✓ OpenAI API Key configured")
            print(f"   ✓ Default Provider: {settings_data['default_model_provider']}")
            print(f"   ✓ Default Model: {settings_data['default_model_name']}")
            
            return True

        except Exception as e:
            await session.rollback()
            print(f"❌ Failed to seed admin: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🔧 Running SQL admin seed script...")
    success = asyncio.run(seed_admin())
    sys.exit(0 if success else 1)
