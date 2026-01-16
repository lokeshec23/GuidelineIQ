
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from ingest import processor
    print("✅ Successfully imported ingest.processor")
except Exception as e:
    print(f"❌ Failed to import ingest.processor: {e}")
    sys.exit(1)
