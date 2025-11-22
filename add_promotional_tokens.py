#!/usr/bin/env python3
"""
Script to add promotional tokens to a user by email.
Can be run locally or on Heroku via: heroku run python add_promotional_tokens.py <email> <amount>
"""

import sys
import os
from datetime import datetime, timezone, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def add_promotional_tokens(email: str, amount: int):
    """Add promotional tokens to a user by email."""
    from src.shared.auth.database import get_db, User
    from src.shared.payment.token_utils import add_tokens
    
    db = next(get_db())
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"Error: User with email '{email}' not found")
            return False
        
        # Add promotional tokens (expire in 1 year)
        expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        
        transaction = add_tokens(
            db=db,
            user_id=user.id,
            amount=amount,
            token_type='free',
            source='promotional',
            expires_at=expires_at,
            metadata={
                'granted_by': 'admin_script',
                'grant_date': datetime.now(timezone.utc).isoformat(),
                'reason': 'promotional_grant'
            }
        )
        
        db.commit()
        
        print(f"Successfully added {amount} promotional tokens to {email} (user_id: {user.id})")
        print(f"Transaction ID: {transaction.id}")
        print(f"Tokens expire on: {expires_at.isoformat()}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python add_promotional_tokens.py <email> <amount>")
        print("Example: python add_promotional_tokens.py nh11092@gmail.com 100")
        sys.exit(1)
    
    email = sys.argv[1]
    try:
        amount = int(sys.argv[2])
    except ValueError:
        print("Error: Amount must be a number")
        sys.exit(1)
    
    if amount <= 0:
        print("Error: Amount must be positive")
        sys.exit(1)
    
    success = add_promotional_tokens(email, amount)
    sys.exit(0 if success else 1)

