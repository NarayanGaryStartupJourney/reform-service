"""Admin routes for managing users and system settings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.shared.auth.database import get_db, User
from src.shared.admin.dependencies import verify_admin
from src.shared.payment.token_utils import add_tokens
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["admin"])


class VerifyPTResponse(BaseModel):
    """Response schema for PT verification."""
    username: str
    is_pt: bool
    message: str


class AddTokensRequest(BaseModel):
    """Request schema for adding tokens."""
    email: str
    amount: int
    source: str = "promotional"
    expires_days: Optional[int] = 365  # Default to 1 year expiration


class AddTokensResponse(BaseModel):
    """Response schema for adding tokens."""
    email: str
    user_id: str
    amount: int
    source: str
    transaction_id: str
    expires_at: str
    message: str


@router.post("/users/{username}/verify-pt", response_model=VerifyPTResponse, status_code=status.HTTP_200_OK)
async def verify_pt_status(
    username: str,
    admin_user: User = Depends(verify_admin),  # Verify admin secret AND user is_admin=True
    db: Session = Depends(get_db)
):
    """
    Verify a user's Personal Trainer status.
    
    Requires:
    1. X-Admin-Secret header with valid admin secret
    2. Authenticated user with is_admin=True
    
    Sets the user's is_pt field to True.
    """
    # Find user by username
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username '{username}' not found"
        )
    
    # Update is_pt status
    user.is_pt = True
    db.commit()
    db.refresh(user)
    
    return VerifyPTResponse(
        username=user.username,
        is_pt=user.is_pt,
        message=f"User '{username}' has been verified as a Personal Trainer"
    )


@router.post("/tokens/add", response_model=AddTokensResponse, status_code=status.HTTP_200_OK)
async def add_tokens_to_user(
    request: AddTokensRequest,
    admin_user: User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """
    Add tokens to a user by email.
    
    Requires:
    1. X-Admin-Secret header with valid admin secret
    2. Authenticated user with is_admin=True
    
    Args:
        request: AddTokensRequest with email, amount, source, and expires_days
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{request.email}' not found"
        )
    
    if request.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    # Calculate expiration date
    expires_at = None
    if request.expires_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_days)
    
    # Add tokens
    transaction = add_tokens(
        db=db,
        user_id=user.id,
        amount=request.amount,
        token_type='free',
        source=request.source,
        expires_at=expires_at,
        metadata={
            'granted_by': 'admin',
            'admin_user_id': admin_user.id,
            'grant_date': datetime.now(timezone.utc).isoformat(),
            'reason': 'admin_grant'
        }
    )
    
    db.commit()
    
    return AddTokensResponse(
        email=user.email,
        user_id=user.id,
        amount=request.amount,
        source=request.source,
        transaction_id=str(transaction.id),
        expires_at=expires_at.isoformat() if expires_at else None,
        message=f"Successfully added {request.amount} {request.source} tokens to {user.email}"
    )

