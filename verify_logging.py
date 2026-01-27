
import sys
import os

# Add backend to path to import utils
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from utils.logger import setup_logger, user_context
import time

def test_logging():
    logger = setup_logger("test_logger")
    
    print("Testing default context...")
    logger.info("This is a log with default context")
    
    print("Testing custom context...")
    token = user_context.set({"username": "testuser", "email": "test@example.com"})
    logger.info("This is a log with USER context")
    logger.error("An error log with USER context")
    user_context.reset(token)
    
    logger.info("Back to default context")

    # Check log file
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "logs", "app.log")
    if os.path.exists(log_file):
        print(f"\n✅ Log file created at: {log_file}")
        with open(log_file, "r") as f:
            print("\n--- Log File Content ---")
            print(f.read())
            print("------------------------")
    else:
        print(f"\n❌ Log file NOT found at: {log_file}")

if __name__ == "__main__":
    test_logging()
