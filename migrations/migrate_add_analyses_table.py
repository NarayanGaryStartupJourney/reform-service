#!/usr/bin/env python3
"""
Migration script to create analyses table for analysis history feature.

This script:
1. Creates analyses table to store video analysis results for logged-in users
2. Creates indexes for efficient querying (user history, filtering by exercise, score, etc.)
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError

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

engine = create_engine(DATABASE_URL)


def table_exists(connection, table_name):
    """Check if a table exists."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def run_migration():
    print("Running migration to create analyses table...")
    print(f"Database: {engine.url.host}:{engine.url.port}/{engine.url.database}")
    print()

    with engine.connect() as connection:
        # Check if users table exists (required for foreign key)
        print("1. Checking users table...")
        if not table_exists(connection, 'users'):
            print("   ERROR: users table does not exist. Please run initial migration first.")
            sys.exit(1)
        print("   ✓ Users table exists.")

        # Create analyses table
        print("\n2. Checking analyses table...")
        if not table_exists(connection, 'analyses'):
            print("   Creating analyses table...")
            connection.execute(text("""
                CREATE TABLE analyses (
                    id UUID PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    exercise INTEGER NOT NULL,
                    exercise_name VARCHAR NOT NULL,
                    score INTEGER NOT NULL,
                    frame_count INTEGER NOT NULL,
                    fps INTEGER NOT NULL,
                    calculation_results JSONB NOT NULL,
                    form_analysis JSONB NOT NULL,
                    camera_angle_info JSONB,
                    phases JSONB,
                    visualization_url VARCHAR,
                    visualization_filename VARCHAR,
                    filename VARCHAR NOT NULL,
                    file_size INTEGER NOT NULL,
                    notes TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_analyses_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """))
            print("   ✓ Created analyses table.")
            
            # Create indexes
            print("   Creating indexes on analyses table...")
            connection.execute(text("CREATE INDEX idx_analyses_user_id ON analyses(user_id)"))
            connection.execute(text("CREATE INDEX idx_analyses_created_at ON analyses(created_at)"))
            connection.execute(text("CREATE INDEX idx_analyses_exercise ON analyses(exercise)"))
            connection.execute(text("CREATE INDEX idx_analyses_score ON analyses(score)"))
            connection.execute(text("CREATE INDEX idx_analyses_user_created ON analyses(user_id, created_at)"))
            connection.execute(text("CREATE INDEX idx_analyses_exercise_score ON analyses(exercise, score)"))
            print("   ✓ Created all indexes.")
        else:
            print("   ✓ Table 'analyses' already exists.")

        # Commit all changes
        connection.commit()
        print("\n✓ Migration completed successfully!")
        print("\nSummary:")
        print("  - Created analyses table with all required columns")
        print("  - Created indexes for efficient querying:")
        print("    * User history queries (user_id + created_at)")
        print("    * Exercise filtering (exercise)")
        print("    * Score filtering (score)")
        print("    * Combined queries (exercise + score)")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n✗ Migration failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

