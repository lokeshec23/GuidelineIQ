import sys
import os
import time

print("--- STARTING VERIFICATION SCRIPT ---", flush=True)

# Add backend directory to path
backend_path = os.path.abspath("backend")
print(f"Adding to path: {backend_path}", flush=True)
sys.path.append(backend_path)

try:
    print("Importing auth.schemas...", flush=True)
    from auth.schemas import UserCreate
    from pydantic import ValidationError
    print("✅ Successfully imported UserCreate schema", flush=True)
except ImportError as e:
    print(f"❌ Failed to import: {e}", flush=True)
    # Print sys.path to help debug
    print(f"sys.path: {sys.path}", flush=True)
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error during import: {e}", flush=True)
    sys.exit(1)

def test_password_validation():
    print("\n--- Testing Password Validation ---", flush=True)
    
    # Test Case 1: Valid Password
    try:
        print("Testing valid password...", flush=True)
        UserCreate(username="testuser", email="test@example.com", password="validpassword", role="user")
        print("✅ VALID (length 13): Accepted as expected", flush=True)
    except ValidationError as e:
        print(f"❌ VALID (length 13): Unexpectedly failed - {e}", flush=True)
    except Exception as e:
        print(f"❌ VALID (length 13): Error - {e}", flush=True)

    # Test Case 2: Too Short
    try:
        print("Testing short password...", flush=True)
        UserCreate(username="testuser", email="test@example.com", password="short", role="user")
        print("❌ SHORT (length 5): Unexpectedly accepted", flush=True)
    except ValidationError as e:
        print("✅ SHORT (length 5): Rejected as expected", flush=True)

    # Test Case 3: Too Long
    try:
        print("Testing long password...", flush=True)
        UserCreate(username="testuser", email="test@example.com", password="thispasswordistoolongfrothelimit", role="user")
        print("❌ LONG (length 32): Unexpectedly accepted", flush=True)
    except ValidationError as e:
        print("✅ LONG (length 32): Rejected as expected", flush=True)

if __name__ == "__main__":
    test_password_validation()
    print("--- DONE ---", flush=True)
