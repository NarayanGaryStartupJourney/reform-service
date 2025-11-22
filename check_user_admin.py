#!/usr/bin/env python3
"""
Script to check if a user is an admin by email.
Usage: python check_user_admin.py <email>
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_user_admin(email: str):
    """Check if a user is an admin by email."""
    from src.shared.auth.database import get_db, User
    
    db = next(get_db())
    
    try:
        # Find user by email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"User with email '{email}' not found")
            return False
        
        is_admin = getattr(user, 'is_admin', False)
        
        print(f"Email: {user.email}")
        print(f"User ID: {user.id}")
        print(f"Full Name: {user.full_name}")
        print(f"Is Admin: {is_admin}")
        
        return is_admin
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_user_admin.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    is_admin = check_user_admin(email)
    sys.exit(0 if is_admin else 1)

