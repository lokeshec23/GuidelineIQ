
import pyodbc
import sys

# Configuration
DB_SERVER = "localhost"
DB_PORT = "1433"
DB_USER = "sa"
DB_PASSWORD = "Loandna@2026"
DB_NAME = "guidelineiq_db"

conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DB_SERVER},{DB_PORT};DATABASE={DB_NAME};UID={DB_USER};PWD={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=yes"

def reset_table():
    print("🚀 Resetting 'files' table...")
    sys.stdout.flush()
    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        print("🔥 Dropping 'files' table...")
        sys.stdout.flush()
        try:
            cursor.execute("DROP TABLE files")
            print("✅ Successfully dropped 'files' table.")
        except pyodbc.Error as e:
            print(f"ℹ️ Table drop warning (might not exist): {e}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    
    sys.stdout.flush()

if __name__ == "__main__":
    reset_table()
    print("🏁 Reset finished. Restart the app to recreate the table.")
    sys.stdout.flush()
