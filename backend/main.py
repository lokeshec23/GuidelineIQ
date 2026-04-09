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
from auth.routes import router as auth_router, sso_router
from settings.routes import router as settings_router
from ingest.routes import router as ingest_router
from compare.routes import router as compare_router
from history.routes import router as history_router
from prompts.routes import router as prompts_router
from chat.routes import router as chat_router
from settings.dscr_routes import router as dscr_params_router
from settings.investor_routes import router as investor_router
from scripts.seed_admin import seed_admin
from scripts.seed_parameters import seed_parameters

# Startup/Shutdown Management
from contextlib import asynccontextmanager
from sql_database import init_db, close_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Initializing database...")
    await init_db()
    
    # Automatic seeding
    logger.info("Running automatic seeding scripts...")
    try:
        await seed_admin()
        await seed_parameters()
        logger.info("✅ Seeding completed successfully")
    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")

    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    await close_db()
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
app.include_router(sso_router)
app.include_router(settings_router)
app.include_router(ingest_router)
app.include_router(compare_router)
app.include_router(history_router)
app.include_router(prompts_router)
app.include_router(chat_router)
app.include_router(dscr_params_router)
app.include_router(investor_router)

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
