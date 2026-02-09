
import pyodbc
import sys

# Configuration
DB_SERVER = "localhost"
DB_PORT = "1433"
DB_USER = "sa"
DB_PASSWORD = "Loandna@2026"
DB_NAME = "guidelineiq_db"

conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER},{DB_PORT};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=yes"

def run_migration():
    print("🚀 Migration starting...")
    sys.stdout.flush()
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        print(f"✅ Connected to {DB_NAME}")
        sys.stdout.flush()

        # Rename column
        try:
            print("🔄 Attempting to rename 'upload_date' to 'created_at' in 'files'...")
            sys.stdout.flush()
            cursor.execute("EXEC sp_rename 'files.upload_date', 'created_at', 'COLUMN'")
            print("✅ Successfully renamed column.")
        except pyodbc.Error as e:
            if "207" in str(e) or "42S22" in str(e) or "Either the parameter @objname is ambiguous" in str(e):
                print(f"ℹ️ Migration skipped: {e}")
            else:
                print(f"⚠️ Warning during rename: {e}")
        
        sys.stdout.flush()
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.stdout.flush()

if __name__ == "__main__":
    run_migration()
    print("🏁 Migration finished.")
    sys.stdout.flush()
