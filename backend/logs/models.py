# backend/logs/models.py

import database
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from bson import ObjectId


async def get_all_logs(
    skip: int = 0,
    limit: int = 100,
    operation: Optional[str] = None,
    level: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> tuple[List[Dict], int]:
    """
    Retrieve activity logs with filtering and pagination.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        operation: Filter by operation type
        level: Filter by log level
        user_id: Filter by user ID
        start_date: Filter logs after this date
        end_date: Filter logs before this date
        
    Returns:
        Tuple of (logs list, total count)
    """
    if database.activity_logs_collection is None:
        raise ConnectionError("Database not initialized")
    
    # Build filter query
    query = {}
    
    if operation:
        query["operation"] = operation
    
    if level:
        query["level"] = level
    
    if user_id:
        query["user_id"] = user_id
    
    if start_date or end_date:
        query["timestamp"] = {}
        if start_date:
            query["timestamp"]["$gte"] = start_date
        if end_date:
            query["timestamp"]["$lte"] = end_date
    
    # Get total count
    total = await database.activity_logs_collection.count_documents(query)
    
    # Get paginated results
    cursor = database.activity_logs_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    
    logs = []
    async for doc in cursor:
        logs.append({
            "id": str(doc["_id"]),
            "user_id": doc.get("user_id", ""),
            "username": doc.get("username", ""),
            "display_name": doc.get("display_name", doc.get("username", "")),
            "operation": doc.get("operation", ""),
            "level": doc.get("level", "INFO"),
            "status": doc.get("status", "success"),
            "details": doc.get("details", {}),
            "error_message": doc.get("error_message"),
            "stack_trace": doc.get("stack_trace"),
            "timestamp": doc.get("timestamp")
        })
    
    return logs, total


async def get_user_logs(
    user_id: str,
    skip: int = 0,
    limit: int = 100,
    operation: Optional[str] = None
) -> tuple[List[Dict], int]:
    """
    Retrieve logs for a specific user.
    
    Args:
        user_id: User ID to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return
        operation: Optional operation type filter
        
    Returns:
        Tuple of (logs list, total count)
    """
    return await get_all_logs(
        skip=skip,
        limit=limit,
        operation=operation,
        user_id=user_id
    )


async def get_logs_stats() -> Dict:
    """
    Get statistics about activity logs.
    
    Returns:
        Dictionary with various statistics
    """
    if database.activity_logs_collection is None:
        raise ConnectionError("Database not initialized")
    
    # Total logs count
    total_logs = await database.activity_logs_collection.count_documents({})
    
    # Count by operation type
    operations_pipeline = [
        {"$group": {"_id": "$operation", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    operations_cursor = database.activity_logs_collection.aggregate(operations_pipeline)
    operations_stats = []
    async for doc in operations_cursor:
        operations_stats.append({
            "operation": doc["_id"],
            "count": doc["count"]
        })
    
    # Count by level
    levels_pipeline = [
        {"$group": {"_id": "$level", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    levels_cursor = database.activity_logs_collection.aggregate(levels_pipeline)
    levels_stats = []
    async for doc in levels_cursor:
        levels_stats.append({
            "level": doc["_id"],
            "count": doc["count"]
        })
    
    # Most active users (top 10)
    users_pipeline = [
        {"$group": {"_id": "$user_id", "username": {"$first": "$username"}, "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    users_cursor = database.activity_logs_collection.aggregate(users_pipeline)
    users_stats = []
    async for doc in users_cursor:
        users_stats.append({
            "user_id": doc["_id"],
            "username": doc.get("username", "Unknown"),
            "activity_count": doc["count"]
        })
    
    # Recent errors (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_errors = await database.activity_logs_collection.count_documents({
        "level": {"$in": ["ERROR", "CRITICAL"]},
        "timestamp": {"$gte": yesterday}
    })
    
    return {
        "total_logs": total_logs,
        "operations": operations_stats,
        "levels": levels_stats,
        "most_active_users": users_stats,
        "recent_errors_24h": recent_errors
    }


async def delete_old_logs(days: int = 90) -> int:
    """
    Delete logs older than specified number of days.
    
    Args:
        days: Number of days to keep logs
        
    Returns:
        Number of deleted logs
    """
    if database.activity_logs_collection is None:
        raise ConnectionError("Database not initialized")
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    result = await database.activity_logs_collection.delete_many({
        "timestamp": {"$lt": cutoff_date}
    })
    
    return result.deleted_count


async def export_logs_data(
    operation: Optional[str] = None,
    level: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict]:
    """
    Export logs data for CSV/Excel generation.
    
    Returns all matching logs without pagination.
    """
    logs, _ = await get_all_logs(
        skip=0,
        limit=10000,  # Large limit for export
        operation=operation,
        level=level,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return logs
