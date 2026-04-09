import os
import sys
import asyncio
from dotenv import load_dotenv
from sqlalchemy.future import select

# Add parent directory to path to import from backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sql_database import AsyncSessionLocal, init_db
from models.sql_models import User
from auth.utils import hash_password

async def seed_random_users():
    """
    Creates specific random users in the SQL database.
    """
    # Ensure database and tables are initialized
    await init_db()
    
    users_to_create = [
        {"username": "lokesh", "email": "lokesh@gmail.com", "password": "Lokesh@2001"},
        {"username": "nisha", "email": "nisha@gmail.com", "password": "Nisha@2001"},
        {"username": "ram", "email": "ram@gmail.com", "password": "Ram@2001"},
        {"username": "dilip", "email": "dilip@gmail.com", "password": "Dilip@2001"},
        {"username": "dustin", "email": "dustin@gmail.com", "password": "Dustin@2001"},
    ]
    
    async with AsyncSessionLocal() as session:
        try:
            for user_data in users_to_create:
                # Check if user already exists
                result = await session.execute(select(User).where(User.email == user_data["email"]))
                existing_user = result.scalars().first()
                
                if existing_user:
                    print(f"User already exists: {existing_user.email}")
                else:
                    new_user = User(
                        username=user_data["username"],
                        email=user_data["email"],
                        hashed_password=hash_password(user_data["password"]),
                        role="user",
                        is_admin=False,
                        is_active=True
                    )
                    session.add(new_user)
                    print(f"User created successfully: {user_data['email']}")
            
            await session.commit()
            print("\nSeed script completed successfully!")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"Failed to seed users: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("Running SQL random users seed script...")
    success = asyncio.run(seed_random_users())
    sys.exit(0 if success else 1)
