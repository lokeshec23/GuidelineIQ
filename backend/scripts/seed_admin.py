# scripts/seed_admin.py

import os
import sys
import asyncio
from dotenv import load_dotenv
from datetime import datetime

# Add parent directory to path to import from backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from auth.utils import hash_password
from settings.models import create_or_update_settings

async def seed_admin():
    """
    Creates the admin user if it doesn't already exist.
    Reads credentials from environment variables and initializes admin settings.
    """
    # Initialize database
    database.get_database()
    
    # Load environment variables
    load_dotenv()
    
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    
    if not admin_email or not admin_password:
        print("❌ Error: ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env file")
        return False
    
    # Check if admin already exists
    existing_admin = await database.users_collection.find_one({"role": "admin"})
    
    if existing_admin:
        print(f"✅ Admin user already exists: {existing_admin['email']}")
        admin_id = str(existing_admin["_id"])
    else:
        # Create admin user
        admin_data = {
            "username": admin_username,
            "email": admin_email,
            "password": hash_password(admin_password),
            "role": "admin"
        }
        
        try:
            result = await database.users_collection.insert_one(admin_data)
            admin_id = str(result.inserted_id)
            print(f"✅ Admin user created successfully!")
            print(f"   Email: {admin_email}")
            print(f"   ID: {admin_id}")
        except Exception as e:
            print(f"❌ Failed to create admin user: {e}")
            return False
    
    # Initialize admin settings from environment variables
    print("\n🔧 Initializing admin settings from environment variables...")
    
    settings_data = {
        "user_id": admin_id,
        "updated_at": datetime.utcnow(),
        
        # API Keys
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        
        # Azure OpenAI Configuration
        "openai_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "openai_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        
        # Default Model Configuration
        "default_model_provider": os.getenv("DEFAULT_MODEL_PROVIDER", "gemini"),
        "default_model_name": os.getenv("DEFAULT_MODEL_NAME", "gemini-2.5-pro"),
        
        # LLM Parameters (with defaults)
        "temperature": float(os.getenv("DEFAULT_TEMPERATURE", "0.3")),
        "max_output_tokens": int(os.getenv("DEFAULT_MAX_TOKENS", "8192")),
        "top_p": float(os.getenv("DEFAULT_TOP_P", "0.95")),
        "stop_sequences": [],
        
        # PDF Chunking
        "pages_per_chunk": int(os.getenv("DEFAULT_PAGES_PER_CHUNK", "5")),
        
        # Comparison settings
        "comparison_chunk_size": int(os.getenv("COMPARISON_CHUNK_SIZE", "10")),
        "max_comparison_chunks": int(os.getenv("MAX_COMPARISON_CHUNKS", "0"))
    }
    
    try:
        await create_or_update_settings(admin_id, settings_data)
        print("✅ Admin settings initialized successfully!")
        
        # Print configured settings
        if settings_data.get("gemini_api_key"):
            print(f"   ✓ Gemini API Key: {'*' * 20}{settings_data['gemini_api_key'][-4:]}")
        if settings_data.get("openai_api_key"):
            print(f"   ✓ OpenAI API Key: {'*' * 20}{settings_data['openai_api_key'][-4:]}")
        if settings_data.get("openai_endpoint"):
            print(f"   ✓ Azure Endpoint: {settings_data['openai_endpoint']}")
        if settings_data.get("openai_deployment"):
            print(f"   ✓ Azure Deployment: {settings_data['openai_deployment']}")
        print(f"   ✓ Default Provider: {settings_data['default_model_provider']}")
        print(f"   ✓ Default Model: {settings_data['default_model_name']}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize admin settings: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Running admin seed script...")
    success = asyncio.run(seed_admin())
    sys.exit(0 if success else 1)
