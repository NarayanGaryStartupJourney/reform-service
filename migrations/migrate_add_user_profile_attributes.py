#!/usr/bin/env python3
"""
Migration script to add user profile attributes:
- technical_level (beginner, novice, intermediate, advanced, elite)
- favorite_exercise (favorite exercise selection)
- community_preference (share_to_similar_levels, share_to_pt, compete_with_someone)
Run this script to add these columns to existing databases.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is required.")
    sys.exit(1)

# Heroku uses postgres:// but SQLAlchemy 2.0+ requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def check_column_exists(connection, table_name, column_name):
    """Check if a column exists in a table."""
    query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name AND column_name = :column_name
    """)
    result = connection.execute(query, {"table_name": table_name, "column_name": column_name})
    return result.fetchone() is not None

def add_profile_attributes():
    """Add profile attribute columns to users table if they don't exist."""
    with engine.begin() as connection:
        try:
            # Add technical_level column
            if not check_column_exists(connection, "users", "technical_level"):
                print("Adding 'technical_level' column to 'users' table...")
                connection.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN technical_level VARCHAR
                """))
                print("✓ Successfully added 'technical_level' column.")
            else:
                print("✓ Column 'technical_level' already exists in 'users' table.")
            
            # Add favorite_exercise column
            if not check_column_exists(connection, "users", "favorite_exercise"):
                print("Adding 'favorite_exercise' column to 'users' table...")
                connection.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN favorite_exercise VARCHAR
                """))
                print("✓ Successfully added 'favorite_exercise' column.")
            else:
                print("✓ Column 'favorite_exercise' already exists in 'users' table.")
            
            # Add community_preference column
            if not check_column_exists(connection, "users", "community_preference"):
                print("Adding 'community_preference' column to 'users' table...")
                connection.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN community_preference VARCHAR
                """))
                print("✓ Successfully added 'community_preference' column.")
            else:
                print("✓ Column 'community_preference' already exists in 'users' table.")
                
        except ProgrammingError as e:
            print(f"ERROR: Database error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    print("Running migration to add user profile attributes...")
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'local'}")
    print()
    add_profile_attributes()
    print()
    print("Migration completed successfully!")

