# main.py
import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import setup_logger
from utils.middleware import LogContextMiddleware

# Setup logger
logger = setup_logger(__name__)


# Load environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Disable SSL warnings
os.environ.pop("REQUESTS_CA_BUNDLE", None)
os.environ["AZURE_CLI_DISABLE_CONNECTION_VERIFICATION"] = "1"

# Import routers
from auth.routes import router as auth_router
from settings.routes import router as settings_router
from ingest.routes import router as ingest_router
from compare.routes import router as compare_router
from history.routes import router as history_router
from prompts.routes import router as prompts_router
from chat.routes import router as chat_router

# Startup/Shutdown Management
from contextlib import asynccontextmanager
from database import db_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup and shutdown events.
    """
    # Startup
    await db_manager.connect()
    await db_manager.connect()
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    await db_manager.close()
    logger.info("Application shut down")


# Initialize FastAPI
app = FastAPI(
    title="Guideline Extraction & Comparison System",
    description="Extract and compare mortgage guidelines using custom prompts",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Logging Middleware
app.add_middleware(LogContextMiddleware)


# Include routers
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(ingest_router)
app.include_router(compare_router)
app.include_router(history_router)
app.include_router(prompts_router)
app.include_router(chat_router)

# Health check
@app.get("/")
def root():
    return {
        "message": "✅ Guideline Extraction & Comparison System API",
        "version": "2.0.0",
        "endpoints": {
            "auth": "/auth",
            "settings": "/settings",
            "ingest": "/ingest",
            "compare": "/compare",
            "history": "/history",
            "prompts": "/prompts",
            "chat": "/chat",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)