import pyodbc
import os
from dotenv import load_dotenv

def create_database():
    load_dotenv()
    
    server = os.getenv("DB_SERVER", "localhost")
    port = os.getenv("DB_PORT", "1433")
    user = os.getenv("DB_USER", "sa")
    password = os.getenv("DB_PASSWORD", "Loandna@2026")
    db_name = os.getenv("DB_NAME", "guidelineiq_db_demo")
    # db_name = os.getenv("DB_NAME", "guidelineiq_db")
    
    print(f"Connecting to {server}:{port} as {user}...")
    
    try:
        # Connect to master to create the new database
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={server},{port};"
            f"DATABASE=master;"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"
        )
        
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{db_name}'")
        row = cursor.fetchone()
        
        if row:
            print(f"Database '{db_name}' already exists.")
        else:
            print(f"Creating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE [{db_name}]")
            print(f"Database '{db_name}' created successfully.")
            
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    create_database()
