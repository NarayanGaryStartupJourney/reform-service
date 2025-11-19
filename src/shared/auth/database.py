"""Database setup and configuration."""

from sqlalchemy import create_engine, Column, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

# Use SQLite for simplicity (can be upgraded to PostgreSQL later)
# On Heroku, use /tmp for SQLite database (ephemeral but writable)
# If DATABASE_URL is set and is PostgreSQL, use that instead
default_db_url = "sqlite:///./reform.db"
if os.environ.get("DYNO"):  # Heroku
    # Use /tmp for SQLite on Heroku (ephemeral filesystem)
    default_db_url = "sqlite:////tmp/reform.db"
elif os.environ.get("DATABASE_URL") and not os.environ.get("DATABASE_URL").startswith("sqlite"):
    # If DATABASE_URL is set and is not SQLite (e.g., PostgreSQL), use it
    default_db_url = os.environ.get("DATABASE_URL")

DATABASE_URL = os.environ.get("DATABASE_URL", default_db_url)

# SQLite-specific connection args
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}
    # Ensure directory exists for SQLite
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        if db_path != ":memory:":
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)


def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # Log error but don't raise - database will be created on first use
        import logging
        logging.warning(f"Database initialization warning: {str(e)}")
        # Try to create tables anyway - this handles case where some tables exist
        try:
            Base.metadata.create_all(bind=engine, checkfirst=True)
        except Exception as e2:
            logging.error(f"Database initialization error: {str(e2)}")
            raise


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

