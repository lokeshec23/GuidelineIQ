
import sys
import os

# Add backend to sys.path
sys.path.append(os.path.abspath('C:/Users/lsaravanan/Lokesh_ws/GuidelineIQ/backend'))

try:
    print("Attempting to import backend.compare.routes...")
    from compare import routes
    print("Import successful!")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
