# backend/logs/routes.py

import io
import csv
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime
from logs.models import get_all_logs, get_user_logs, get_logs_stats, export_logs_data
from logs.schemas import LogsResponse, LogEntry, LogFilter, LogStats
from auth.middleware import require_admin
from auth.utils import verify_token
from fastapi import Header
from bson import ObjectId
import database

router = APIRouter(prefix="/logs", tags=["Activity Logs"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


async def get_current_user_from_token(authorization: str = Header(...)) -> dict:
    """Extract and validate user from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token does not contain a user ID")
    
    if database.users_collection is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    user = await database.users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.get("", response_model=LogsResponse)
async def get_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    operation: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    admin_user: dict = Depends(require_admin)
):
    """
    Get all activity logs with filtering and pagination (Admin only).
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of logs per page (default: 50, max: 200)
    - operation: Filter by operation type
    - level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - user_id: Filter by user ID
    - start_date: Filter logs after this date (ISO format)
    - end_date: Filter logs before this date (ISO format)
    """
    skip = (page - 1) * page_size
    
    logs, total = await get_all_logs(
        skip=skip,
        limit=page_size,
        operation=operation,
        level=level,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return LogsResponse(
        logs=[LogEntry(**log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/me", response_model=LogsResponse)
async def get_my_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    operation: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get activity logs for the current user.
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of logs per page (default: 50, max: 200)
    - operation: Filter by operation type
    """
    user_id = str(current_user["_id"])
    skip = (page - 1) * page_size
    
    logs, total = await get_user_logs(
        user_id=user_id,
        skip=skip,
        limit=page_size,
        operation=operation
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return LogsResponse(
        logs=[LogEntry(**log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/user/{user_id}", response_model=LogsResponse)
async def get_user_logs_route(
    user_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    operation: Optional[str] = Query(None),
    admin_user: dict = Depends(require_admin)
):
    """
    Get activity logs for a specific user (Admin only).
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of logs per page (default: 50, max: 200)
    - operation: Filter by operation type
    """
    skip = (page - 1) * page_size
    
    logs, total = await get_user_logs(
        user_id=user_id,
        skip=skip,
        limit=page_size,
        operation=operation
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    return LogsResponse(
        logs=[LogEntry(**log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/stats", response_model=LogStats)
async def get_stats(admin_user: dict = Depends(require_admin)):
    """
    Get activity log statistics (Admin only).
    
    Returns:
    - Total log count
    - Top 10 operations by count
    - Log counts by level
    - Top 10 most active users
    - Recent errors (last 24 hours)
    """
    stats = await get_logs_stats()
    return LogStats(**stats)


@router.get("/export")
async def export_logs(
    operation: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    admin_user: dict = Depends(require_admin)
):
    """
    Export activity logs as CSV (Admin only).
    
    Query Parameters:
    - operation: Filter by operation type
    - level: Filter by log level
    - user_id: Filter by user ID
    - start_date: Filter logs after this date
    - end_date: Filter logs before this date
    """
    logs = await export_logs_data(
        operation=operation,
        level=level,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'timestamp', 'username', 'user_id', 'operation', 'level', 
        'status', 'details', 'error_message'
    ])
    
    writer.writeheader()
    for log in logs:
        writer.writerow({
            'timestamp': log['timestamp'].isoformat() if log.get('timestamp') else '',
            'username': log.get('username', ''),
            'user_id': log.get('user_id', ''),
            'operation': log.get('operation', ''),
            'level': log.get('level', ''),
            'status': log.get('status', ''),
            'details': str(log.get('details', {})),
            'error_message': log.get('error_message', '')
        })
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=activity_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.websocket("/stream")
async def websocket_logs_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time log streaming (Admin only).
    
    Clients should connect to this endpoint to receive live log updates.
    Authentication is checked via query parameter 'token'.
    """
    # Get token from query parameters
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    
    # Verify token and check admin role
    try:
        from auth.utils import verify_token
        payload = verify_token(token)
        
        if not payload or payload.get("type") != "access":
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Check if user is admin
        if database.users_collection is None:
            await websocket.close(code=1011, reason="Database not initialized")
            return
        
        user = await database.users_collection.find_one({"_id": ObjectId(user_id)})
        if not user or user.get("role") != "admin":
            await websocket.close(code=1008, reason="Admin access required")
            return
    
    except Exception as e:
        print(f"WebSocket authentication error: {e}")
        await websocket.close(code=1011, reason="Authentication failed")
        return
    
    # Accept connection
    await manager.connect(websocket)
    
    try:
        # Send initial connection success message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to log stream",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and listen for client messages
        while True:
            # Wait for any message from client (ping/pong)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back to keep connection alive
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"type": "ping"})
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Helper function to broadcast new logs (called from logging utility)
async def broadcast_log(log_entry: dict):
    """
    Broadcast a new log entry to all connected WebSocket clients.
    This function should be called whenever a new log is created.
    """
    await manager.broadcast({
        "type": "new_log",
        "log": log_entry,
        "timestamp": datetime.utcnow().isoformat()
    })
