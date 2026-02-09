
import pyodbc

# Configuration
DB_SERVER = "localhost"
DB_PORT = "1433"
DB_USER = "sa"
DB_PASSWORD = "Loandna@2026"
DB_NAME = "guidelineiq_db"

conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER},{DB_PORT};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=yes"

print(f"🚀 Connecting to {DB_NAME} using pyodbc...")
try:
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    
    print("🔍 Checking if column 'upload_date' exists...")
    cursor.execute("SELECT col.name FROM sys.columns col JOIN sys.tables tab ON col.object_id = tab.object_id WHERE tab.name = 'files' AND col.name = 'upload_date'")
    if cursor.fetchone():
        print("🔄 Renaming 'upload_date' to 'created_at'...")
        cursor.execute("EXEC sp_rename 'files.upload_date', 'created_at', 'COLUMN'")
        print("✅ Successfully renamed column.")
    else:
        print("ℹ️ Column 'upload_date' not found. It might already be renamed or the table doesn't exist.")
    
    conn.close()
except Exception as e:
    print(f"❌ Migration failed: {e}")
