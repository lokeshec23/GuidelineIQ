# backend/auth/models.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.sql_models import User

async def find_user_by_email(db: AsyncSession, email: str):
    """Find a user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: str):
    """Find a user by their ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

async def create_user(db: AsyncSession, user_data: dict):
    """Create a new user."""
    # Remove 'created_at' if it's string to let SQL server default handle it or parse it
    # But user_data comes from router which sets created_at as string. 
    # Better to pop it and let model handle, OR ensure model accepts it.
    # The SQL model has `created_at` as DateTime.
    
    # Clean up user_data for SQL model
    from datetime import datetime
    if "created_at" in user_data and isinstance(user_data["created_at"], str):
        try:
            user_data["created_at"] = datetime.fromisoformat(user_data["created_at"])
        except:
            user_data.pop("created_at")

    new_user = User(**user_data)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def get_all_users(db: AsyncSession):
    """Retrieve all users from the database."""
    result = await db.execute(select(User))
    return result.scalars().all()