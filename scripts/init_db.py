import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from app.core.config import settings

def init_database():
    """Initialize the MySQL database"""
    try:
        # Connect to MySQL server without database
        conn = mysql.connector.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD
        )
        cursor = conn.cursor()

        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DATABASE}")
        print(f"Database '{settings.MYSQL_DATABASE}' created successfully")

        # Close connection
        cursor.close()
        conn.close()

        # Import and create all tables
        from app.db.database import Base, engine
        Base.metadata.create_all(bind=engine)
        print("All tables created successfully")

    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_database() 