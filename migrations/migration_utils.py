"""
Common utilities for database migrations.

Provides shared functions for checking table/column existence,
database connection, and common migration patterns.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError


def get_database_url():
    """Get and validate DATABASE_URL from environment."""
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required.")
        sys.exit(1)
    
    # Fix Heroku postgres:// URL
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return database_url


def get_engine():
    """Create SQLAlchemy engine from DATABASE_URL."""
    return create_engine(get_database_url())


def table_exists(connection, table_name):
    """Check if a table exists in the database."""
    inspector = inspect(connection)
    return table_name in inspector.get_table_names()


def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table."""
    inspector = inspect(connection)
    columns = inspector.get_columns(table_name)
    return any(c['name'] == column_name for c in columns)


def index_exists(connection, table_name, index_name):
    """Check if an index exists on a table."""
    inspector = inspect(connection)
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def run_migration(migration_name, migration_func):
    """
    Run a migration with consistent error handling.
    
    Args:
        migration_name: Name of the migration (for logging)
        migration_func: Function that performs the migration
    """
    print(f"\n{'='*60}")
    print(f"Running migration: {migration_name}")
    print(f"{'='*60}")
    
    try:
        migration_func()
        print(f"\n✓ Migration '{migration_name}' completed successfully!")
    except Exception as e:
        print(f"\n✗ Migration '{migration_name}' failed: {e}")
        raise

