# utils/progress.py
import threading
import asyncio
from typing import Dict

# Store progress for each session
progress_store: Dict[str, dict] = {}

# threading.Lock for synchronous callers (background threads via asyncio.to_thread)
progress_lock = threading.Lock()

# asyncio.Lock for async callers (route handlers, SSE streams)
_async_progress_lock = asyncio.Lock()


def update_progress(session_id: str, progress: int, message: str):
    """Update progress for a specific session (thread-safe, for sync/background contexts)"""
    with progress_lock:
        progress_store[session_id] = {
            "progress": min(progress, 100),
            "message": message,
        }
        print(f"📊 [{session_id[:8]}] {progress}% - {message}")


async def async_get_progress(session_id: str) -> dict:
    """Get current progress for a session (async-safe, non-blocking)"""
    async with _async_progress_lock:
        return progress_store.get(session_id, {"progress": 0, "message": "Not found"})


async def async_get_progress_data(session_id: str) -> dict:
    """Get raw progress data for a session (async-safe, returns None if not found)"""
    async with _async_progress_lock:
        return progress_store.get(session_id)


async def async_get_session_data(session_id: str) -> dict:
    """Get full session data including preview_data, excel_path etc. (async-safe)"""
    async with _async_progress_lock:
        return progress_store.get(session_id, {}).copy()


def get_progress(session_id: str) -> dict:
    """Get current progress for a session (thread-safe, legacy)"""
    with progress_lock:
        return progress_store.get(session_id, {"progress": 0, "message": "Not found"})


def delete_progress(session_id: str):
    """Remove progress data for a session"""
    with progress_lock:
        if session_id in progress_store:
            del progress_store[session_id]