
import py_compile
import sys
import os

files_to_check = [
    "backend/ingest/dscr_extractor.py",
    "backend/ingest/processor.py",
    "backend/ingest/rag_extractor.py",
    "backend/ingest/routes.py",
    "backend/ingest/dscr_config.py",
    "backend/chat/rag_service.py",
    "backend/main.py"
]

print("Verifying Python syntax...")
has_error = False
for file_path in files_to_check:
    full_path = os.path.abspath(file_path)
    if not os.path.exists(full_path):
        print(f"❌ File not found: {full_path}")
        continue
        
    try:
        py_compile.compile(full_path, doraise=True)
        print(f"✅ Syntax OK: {file_path}")
    except py_compile.PyCompileError as e:
        print(f"❌ Syntax Error in {file_path}:")
        print(e)
        has_error = True
    except Exception as e:
        print(f"❌ Error checking {file_path}: {e}")
        has_error = True

if has_error:
    sys.exit(1)
print("All files passed syntax check.")
