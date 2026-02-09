import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar

# ContextVar to store user info (username, email)
user_context = ContextVar("user_context", default={"username": "System", "email": "system@app.com"})

class ContextFilter(logging.Filter):
    """
    This is a filter which injects user context into the log.
    """
    def filter(self, record):
        try:
            ctx = user_context.get()
            record.user_info = f"{ctx.get('username', 'Unknown')}:{ctx.get('email', 'Unknown')}"
        except Exception:
            record.user_info = "System:system@app.com"
        return True

def setup_logger(name: str):
    logger = logging.getLogger(name)
    
    # Set log level
    logger.setLevel(logging.INFO)
    logger.propagate = False 

    # If logger already has handlers, don't add more, but ensure filter is there
    if not logger.handlers:
        # Create logs directory if it doesn't exist
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "app.log")

        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - [%(user_info)s] - %(name)s - %(levelname)s - %(message)s"
        )

        # File Handler
        try:
            file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Error setting up file handler: {e}")

        # Stream Handler (Console)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # Add filter to the logger itself so all handlers get it
    # First, remove existing ContextFilters to avoid duplicates
    logger.filters = [f for f in logger.filters if not isinstance(f, ContextFilter)]
    logger.addFilter(ContextFilter())

    return logger
