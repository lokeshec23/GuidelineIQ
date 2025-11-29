# backend/auth/models.py

import database

async def find_user_by_email(email: str):
    if database.users_collection is None:
        raise ConnectionError("Database connection is not available.")
    return await database.users_collection.find_one({"email": email})

async def create_user(user_data: dict):
    if database.users_collection is None:
        raise ConnectionError("Database connection is not available.")
    result = await database.users_collection.insert_one(user_data)
    return await database.users_collection.find_one({"_id": result.inserted_id})