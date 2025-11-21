#!/usr/bin/env python3
"""
Migration script to add payment-related tables and user columns:
- token_transactions table (tracks all token credits/debits)
- subscriptions table (tracks user subscriptions)
- payments table (audit trail for payments)
- Add payment-related columns to users table

Note: Stripe integration is not implemented yet. These tables are prepared
for future Stripe integration. All Stripe-related columns are nullable.
Run this script to add these tables and columns to existing databases.
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

def check_table_exists(connection, table_name):
    """Check if a table exists."""
    query = text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = :table_name
    """)
    result = connection.execute(query, {"table_name": table_name})
    return result.fetchone() is not None

def check_column_exists(connection, table_name, column_name):
    """Check if a column exists in a table."""
    query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name AND column_name = :column_name
    """)
    result = connection.execute(query, {"table_name": table_name, "column_name": column_name})
    return result.fetchone() is not None

def add_user_payment_columns():
    """Add payment-related columns to users table."""
    with engine.begin() as connection:
        try:
            # Add stripe_customer_id column
            if not check_column_exists(connection, "users", "stripe_customer_id"):
                print("Adding 'stripe_customer_id' column to 'users' table...")
                connection.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN stripe_customer_id VARCHAR UNIQUE
                """))
                print("✓ Successfully added 'stripe_customer_id' column.")
            else:
                print("✓ Column 'stripe_customer_id' already exists in 'users' table.")
            
            # Add subscription_status column
            if not check_column_exists(connection, "users", "subscription_status"):
                print("Adding 'subscription_status' column to 'users' table...")
                connection.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN subscription_status VARCHAR
                """))
                print("✓ Successfully added 'subscription_status' column.")
            else:
                print("✓ Column 'subscription_status' already exists in 'users' table.")
            
            # Add subscription_tier column
            if not check_column_exists(connection, "users", "subscription_tier"):
                print("Adding 'subscription_tier' column to 'users' table...")
                connection.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN subscription_tier VARCHAR
                """))
                print("✓ Successfully added 'subscription_tier' column.")
            else:
                print("✓ Column 'subscription_tier' already exists in 'users' table.")
                
        except ProgrammingError as e:
            print(f"ERROR: Database error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            sys.exit(1)

def create_token_transactions_table():
    """Create token_transactions table."""
    with engine.begin() as connection:
        try:
            if not check_table_exists(connection, "token_transactions"):
                print("Creating 'token_transactions' table...")
                connection.execute(text("""
                    CREATE TABLE token_transactions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token_type VARCHAR NOT NULL CHECK (token_type IN ('free', 'purchased')),
                        amount INTEGER NOT NULL,
                        source VARCHAR NOT NULL,
                        expires_at TIMESTAMP,
                        stripe_payment_intent_id VARCHAR,
                        stripe_subscription_id VARCHAR,
                        metadata JSONB,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                print("✓ Successfully created 'token_transactions' table.")
                
                # Create indexes
                print("Creating indexes for 'token_transactions' table...")
                connection.execute(text("""
                    CREATE INDEX idx_token_transactions_user_id ON token_transactions(user_id)
                """))
                connection.execute(text("""
                    CREATE INDEX idx_token_transactions_created_at ON token_transactions(created_at)
                """))
                connection.execute(text("""
                    CREATE INDEX idx_token_transactions_stripe_payment_intent ON token_transactions(stripe_payment_intent_id)
                    WHERE stripe_payment_intent_id IS NOT NULL
                """))
                print("✓ Successfully created indexes.")
            else:
                print("✓ Table 'token_transactions' already exists.")
                
        except ProgrammingError as e:
            print(f"ERROR: Database error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            sys.exit(1)

def create_subscriptions_table():
    """Create subscriptions table."""
    with engine.begin() as connection:
        try:
            if not check_table_exists(connection, "subscriptions"):
                print("Creating 'subscriptions' table...")
                connection.execute(text("""
                    CREATE TABLE subscriptions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        stripe_subscription_id VARCHAR UNIQUE,
                        stripe_customer_id VARCHAR NOT NULL,
                        status VARCHAR NOT NULL CHECK (status IN ('active', 'canceled', 'past_due', 'unpaid', 'trialing')),
                        tier VARCHAR NOT NULL,
                        tokens_per_period INTEGER NOT NULL,
                        current_period_start TIMESTAMP,
                        current_period_end TIMESTAMP,
                        cancel_at_period_end BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                print("✓ Successfully created 'subscriptions' table.")
                
                # Create indexes
                print("Creating indexes for 'subscriptions' table...")
                connection.execute(text("""
                    CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id)
                """))
                connection.execute(text("""
                    CREATE INDEX idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id)
                    WHERE stripe_subscription_id IS NOT NULL
                """))
                connection.execute(text("""
                    CREATE INDEX idx_subscriptions_status ON subscriptions(status)
                """))
                print("✓ Successfully created indexes.")
            else:
                print("✓ Table 'subscriptions' already exists.")
                
        except ProgrammingError as e:
            print(f"ERROR: Database error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            sys.exit(1)

def create_payments_table():
    """Create payments table for audit trail."""
    with engine.begin() as connection:
        try:
            if not check_table_exists(connection, "payments"):
                print("Creating 'payments' table...")
                connection.execute(text("""
                    CREATE TABLE payments (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        stripe_payment_intent_id VARCHAR UNIQUE NOT NULL,
                        amount DECIMAL(10, 2) NOT NULL,
                        currency VARCHAR(3) NOT NULL DEFAULT 'usd',
                        status VARCHAR NOT NULL CHECK (status IN ('succeeded', 'failed', 'pending', 'canceled')),
                        payment_type VARCHAR NOT NULL CHECK (payment_type IN ('one_time', 'subscription')),
                        tokens_granted INTEGER,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                print("✓ Successfully created 'payments' table.")
                
                # Create indexes
                print("Creating indexes for 'payments' table...")
                connection.execute(text("""
                    CREATE INDEX idx_payments_user_id ON payments(user_id)
                """))
                connection.execute(text("""
                    CREATE INDEX idx_payments_stripe_payment_intent_id ON payments(stripe_payment_intent_id)
                """))
                connection.execute(text("""
                    CREATE INDEX idx_payments_status ON payments(status)
                """))
                print("✓ Successfully created indexes.")
            else:
                print("✓ Table 'payments' already exists.")
                
        except ProgrammingError as e:
            print(f"ERROR: Database error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    print("Running migration to add payment-related tables and columns...")
    print(f"Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'local'}")
    print()
    
    print("=" * 60)
    print("Step 1: Adding payment columns to users table")
    print("=" * 60)
    add_user_payment_columns()
    print()
    
    print("=" * 60)
    print("Step 2: Creating token_transactions table")
    print("=" * 60)
    create_token_transactions_table()
    print()
    
    print("=" * 60)
    print("Step 3: Creating subscriptions table")
    print("=" * 60)
    create_subscriptions_table()
    print()
    
    print("=" * 60)
    print("Step 4: Creating payments table")
    print("=" * 60)
    create_payments_table()
    print()
    
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    print()
    print("Note: Stripe integration is not yet implemented.")
    print("These tables are ready for future Stripe integration.")

