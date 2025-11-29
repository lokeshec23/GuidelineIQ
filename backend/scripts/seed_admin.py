# scripts/seed_admin.py

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add parent directory to path to import from backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
from auth.utils import hash_password

async def seed_admin():
    """
    Creates the admin user if it doesn't already exist.
    Reads credentials from environment variables.
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
        return True
    
    # Create admin user
    admin_data = {
        "username": admin_username,
        "email": admin_email,
        "password": hash_password(admin_password),
        "role": "admin"
    }
    
    try:
        result = await database.users_collection.insert_one(admin_data)
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {admin_email}")
        print(f"   ID: {result.inserted_id}")
        return True
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Running admin seed script...")
    success = asyncio.run(seed_admin())
    sys.exit(0 if success else 1)
