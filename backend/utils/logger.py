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
        ctx = user_context.get()
        record.user_info = f"{ctx.get('username', 'Unknown')}:{ctx.get('email', 'Unknown')}"
        return True

def setup_logger(name: str):
    logger = logging.getLogger(name)
    
    # If logger is already configured, return it
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False # Prevent double logging if attached to root

    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - [%(user_info)s] - %(name)s - %(levelname)s - %(message)s"
    )

    # File Handler
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5) # 10MB
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ContextFilter())
    logger.addHandler(file_handler)

    # Stream Handler (Console)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(ContextFilter())
    logger.addHandler(stream_handler)

    return logger
