"""
Migration: Change fps column from INTEGER to FLOAT in analyses table.

This migration preserves the original FPS precision (e.g., 29.97 fps) instead of truncating to integer.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Get database URL
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required.")
    sys.exit(1)

# Fix Heroku postgres:// URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def migrate():
    """Change fps column from INTEGER to FLOAT."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if analyses table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'analyses'
            );
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("analyses table does not exist. Skipping migration.")
            return
        
        # Check current column type
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'analyses' AND column_name = 'fps';
        """)
        result = cursor.fetchone()
        
        if not result:
            print("fps column does not exist. Skipping migration.")
            return
        
        current_type = result[0]
        if current_type == 'double precision' or current_type == 'real':
            print(f"fps column is already {current_type}. No migration needed.")
            return
        
        print(f"Current fps column type: {current_type}")
        print("Changing fps column from INTEGER to FLOAT...")
        
        # Alter column type to FLOAT (double precision in PostgreSQL)
        cursor.execute("""
            ALTER TABLE analyses 
            ALTER COLUMN fps TYPE DOUBLE PRECISION;
        """)
        
        print("✓ Successfully changed fps column to DOUBLE PRECISION")
        
        cursor.close()
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    migrate()

