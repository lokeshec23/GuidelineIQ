
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath("backend"))

print("Attempting to import backend.ingest.routes...")
try:
    from backend.ingest import routes
    print("✅ Successfully imported backend.ingest.routes")
except Exception as e:
    print(f"❌ Failed to import backend.ingest.routes: {e}")
    import traceback
    traceback.print_exc()

print("\nAttempting to import backend.ingest.processor...")
try:
    from backend.ingest import processor
    print("✅ Successfully imported backend.ingest.processor")
except Exception as e:
    print(f"❌ Failed to import backend.ingest.processor: {e}")
    traceback.print_exc()
