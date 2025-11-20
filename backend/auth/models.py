# backend/auth/models.py

from database import users_collection

async def find_user_by_email(email: str):
    # ✅ CORRECTED
    if users_collection is None:
        raise ConnectionError("Database connection is not available.")
    return await users_collection.find_one({"email": email})

async def create_user(user_data: dict):
    # ✅ CORRECTED
    if users_collection is None:
        raise ConnectionError("Database connection is not available.")
    result = await users_collection.insert_one(user_data)
    return await users_collection.find_one({"_id": result.inserted_id})