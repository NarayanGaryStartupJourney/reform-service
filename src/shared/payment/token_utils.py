"""Token management utilities for the payment system."""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timezone
from typing import Dict, Optional, List
from src.shared.payment.database import TokenTransaction


class TokenBalance:
    """Represents a user's token balance breakdown."""
    def __init__(self, free_tokens: int = 0, purchased_tokens: int = 0):
        self.free_tokens = free_tokens
        self.purchased_tokens = purchased_tokens
    
    @property
    def total(self) -> int:
        """Total available tokens."""
        return self.free_tokens + self.purchased_tokens
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses."""
        return {
            "free_tokens": self.free_tokens,
            "purchased_tokens": self.purchased_tokens,
            "total_tokens": self.total
        }


def calculate_token_balance(
    db: Session,
    user_id: str,
    include_breakdown: bool = False
) -> TokenBalance:
    """
    Calculate user's current token balance from transactions.
    Returns breakdown of free vs purchased tokens.
    
    Free tokens that have expired are excluded.
    
    Args:
        db: Database session
        user_id: User ID
        include_breakdown: If True, includes breakdown by source in metadata
    
    Returns:
        TokenBalance object with free_tokens, purchased_tokens, and total
    """
    now = datetime.now(timezone.utc)
    
    # Get all valid token transactions (credits minus debits)
    # Free tokens: only count non-expired ones
    free_credits = db.query(func.coalesce(func.sum(TokenTransaction.amount), 0)).filter(
        and_(
            TokenTransaction.user_id == user_id,
            TokenTransaction.token_type == 'free',
            TokenTransaction.amount > 0,
            or_(
                TokenTransaction.expires_at.is_(None),
                TokenTransaction.expires_at > now
            )
        )
    ).scalar() or 0
    
    free_debits = db.query(func.coalesce(func.sum(func.abs(TokenTransaction.amount)), 0)).filter(
        and_(
            TokenTransaction.user_id == user_id,
            TokenTransaction.token_type == 'free',
            TokenTransaction.amount < 0
        )
    ).scalar() or 0
    
    # Purchased tokens: count all (they don't expire)
    purchased_credits = db.query(func.coalesce(func.sum(TokenTransaction.amount), 0)).filter(
        and_(
            TokenTransaction.user_id == user_id,
            TokenTransaction.token_type == 'purchased',
            TokenTransaction.amount > 0
        )
    ).scalar() or 0
    
    purchased_debits = db.query(func.coalesce(func.sum(func.abs(TokenTransaction.amount)), 0)).filter(
        and_(
            TokenTransaction.user_id == user_id,
            TokenTransaction.token_type == 'purchased',
            TokenTransaction.amount < 0
        )
    ).scalar() or 0
    
    # Calculate net balances
    free_tokens = max(0, free_credits - free_debits)
    purchased_tokens = max(0, purchased_credits - purchased_debits)
    
    balance = TokenBalance(free_tokens=free_tokens, purchased_tokens=purchased_tokens)
    
    # Optional: Add breakdown by source if requested
    if include_breakdown:
        # Calculate breakdown for free tokens by source
        free_by_source = {}
        for source_type in ['monthly_allotment', 'promotional', 'signup_bonus', 'referral_bonus']:
            credits = db.query(func.coalesce(func.sum(TokenTransaction.amount), 0)).filter(
                and_(
                    TokenTransaction.user_id == user_id,
                    TokenTransaction.token_type == 'free',
                    TokenTransaction.source == source_type,
                    TokenTransaction.amount > 0,
                    or_(
                        TokenTransaction.expires_at.is_(None),
                        TokenTransaction.expires_at > now
                    )
                )
            ).scalar() or 0
            
            debits = db.query(func.coalesce(func.sum(func.abs(TokenTransaction.amount)), 0)).filter(
                and_(
                    TokenTransaction.user_id == user_id,
                    TokenTransaction.token_type == 'free',
                    TokenTransaction.source == source_type,
                    TokenTransaction.amount < 0
                )
            ).scalar() or 0
            
            net = max(0, credits - debits)
            if net > 0:
                free_by_source[source_type] = net
        
        # Store breakdown in a way that can be accessed (we'll add this to TokenBalance)
        balance._breakdown = {
            'free_by_source': free_by_source,
            'purchased_tokens': purchased_tokens
        }
    
    return balance


def add_tokens(
    db: Session,
    user_id: str,
    amount: int,
    token_type: str,
    source: str,
    expires_at: Optional[datetime] = None,
    stripe_payment_intent_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> TokenTransaction:
    """
    Add tokens to a user's account.
    
    Args:
        db: Database session
        user_id: User ID
        amount: Number of tokens to add (must be positive)
        token_type: 'free' or 'purchased'
        source: Source of tokens (e.g., 'signup_bonus', 'stripe_purchase', 'subscription_monthly')
        expires_at: Expiration date (for free tokens, None for purchased)
        stripe_payment_intent_id: Stripe payment intent ID (for future use)
        stripe_subscription_id: Stripe subscription ID (for future use)
        metadata: Additional metadata as dictionary
    
    Returns:
        Created TokenTransaction
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    if token_type not in ['free', 'purchased']:
        raise ValueError("token_type must be 'free' or 'purchased'")
    
    transaction = TokenTransaction(
        user_id=user_id,
        token_type=token_type,
        amount=amount,
        source=source,
        expires_at=expires_at,
        stripe_payment_intent_id=stripe_payment_intent_id,
        stripe_subscription_id=stripe_subscription_id,
        metadata=metadata
    )
    
    db.add(transaction)
    db.flush()  # Flush to get the ID without committing
    
    return transaction


def deduct_tokens(
    db: Session,
    user_id: str,
    amount: int,
    source: str = 'analysis_usage',
    metadata: Optional[Dict] = None
) -> bool:
    """
    Deduct tokens from a user's account.
    Uses tokens in this order:
    1. Free monthly allotted tokens (source='monthly_allotment')
    2. Promotional tokens (source='promotional')
    3. Other free tokens (signup_bonus, referral_bonus, etc.)
    4. Purchased tokens
    
    Args:
        db: Database session
        user_id: User ID
        amount: Number of tokens to deduct (must be positive)
        source: Source of deduction (default: 'analysis_usage')
        metadata: Additional metadata as dictionary
    
    Returns:
        True if deduction was successful, False if insufficient tokens
    """
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    # Check if user has enough tokens
    balance = calculate_token_balance(db, user_id)
    if balance.total < amount:
        return False
    
    now = datetime.now(timezone.utc)
    remaining_to_deduct = amount
    
    # Order of deduction: monthly_allotment → promotional → other free → purchased
    
    # 1. Deduct from monthly allotted tokens first
    monthly_balance = _calculate_source_balance(
        db, user_id, 'free', 'monthly_allotment', now
    )
    if monthly_balance > 0:
        deduct_amount = min(remaining_to_deduct, monthly_balance)
        if deduct_amount > 0:
            debit = TokenTransaction(
                user_id=user_id,
                token_type='free',
                amount=-deduct_amount,
                source=source,
                metadata={**(metadata or {}), 'deducted_from': 'monthly_allotment'}
            )
            db.add(debit)
            remaining_to_deduct -= deduct_amount
    
    # 2. Deduct from promotional tokens
    if remaining_to_deduct > 0:
        promo_balance = _calculate_source_balance(
            db, user_id, 'free', 'promotional', now
        )
        if promo_balance > 0:
            deduct_amount = min(remaining_to_deduct, promo_balance)
            if deduct_amount > 0:
                debit = TokenTransaction(
                    user_id=user_id,
                    token_type='free',
                    amount=-deduct_amount,
                    source=source,
                    metadata={**(metadata or {}), 'deducted_from': 'promotional'}
                )
                db.add(debit)
                remaining_to_deduct -= deduct_amount
    
    # 3. Deduct from other free tokens (signup_bonus, referral_bonus, etc.)
    # Calculate remaining free tokens after monthly and promotional
    if remaining_to_deduct > 0:
        # Get all free token sources except monthly_allotment and promotional
        other_free_sources = ['signup_bonus', 'referral_bonus']
        other_free_balance = 0
        for other_source in other_free_sources:
            other_free_balance += _calculate_source_balance(
                db, user_id, 'free', other_source, now
            )
        
        # Also account for any free tokens with unknown/other sources
        # by checking total free balance minus what we've accounted for
        total_accounted_free = monthly_balance + promo_balance + other_free_balance
        if balance.free_tokens > total_accounted_free:
            other_free_balance += (balance.free_tokens - total_accounted_free)
        
        if other_free_balance > 0:
            deduct_amount = min(remaining_to_deduct, other_free_balance)
            if deduct_amount > 0:
                debit = TokenTransaction(
                    user_id=user_id,
                    token_type='free',
                    amount=-deduct_amount,
                    source=source,
                    metadata={**(metadata or {}), 'deducted_from': 'other_free'}
                )
                db.add(debit)
                remaining_to_deduct -= deduct_amount
    
    # 4. Deduct from purchased tokens
    if remaining_to_deduct > 0:
        if balance.purchased_tokens >= remaining_to_deduct:
            debit = TokenTransaction(
                user_id=user_id,
                token_type='purchased',
                amount=-remaining_to_deduct,
                source=source,
                metadata={**(metadata or {}), 'deducted_from': 'purchased'}
            )
            db.add(debit)
            remaining_to_deduct = 0
        else:
            # This shouldn't happen if balance check was correct, but handle it
            db.rollback()
            return False
    
    return True


def _calculate_source_balance(
    db: Session,
    user_id: str,
    token_type: str,
    source: str,
    now: datetime
) -> int:
    """
    Helper function to calculate balance for a specific token type and source.
    
    Args:
        db: Database session
        user_id: User ID
        token_type: 'free' or 'purchased'
        source: Source type (e.g., 'monthly_allotment', 'promotional')
        now: Current datetime for expiration checks
    
    Returns:
        Net balance for the specified type and source
    """
    if token_type == 'free':
        credits = db.query(func.coalesce(func.sum(TokenTransaction.amount), 0)).filter(
            and_(
                TokenTransaction.user_id == user_id,
                TokenTransaction.token_type == 'free',
                TokenTransaction.source == source,
                TokenTransaction.amount > 0,
                or_(
                    TokenTransaction.expires_at.is_(None),
                    TokenTransaction.expires_at > now
                )
            )
        ).scalar() or 0
        
        debits = db.query(func.coalesce(func.sum(func.abs(TokenTransaction.amount)), 0)).filter(
            and_(
                TokenTransaction.user_id == user_id,
                TokenTransaction.token_type == 'free',
                TokenTransaction.source == source,
                TokenTransaction.amount < 0
            )
        ).scalar() or 0
    else:  # purchased
        credits = db.query(func.coalesce(func.sum(TokenTransaction.amount), 0)).filter(
            and_(
                TokenTransaction.user_id == user_id,
                TokenTransaction.token_type == 'purchased',
                TokenTransaction.source == source,
                TokenTransaction.amount > 0
            )
        ).scalar() or 0
        
        debits = db.query(func.coalesce(func.sum(func.abs(TokenTransaction.amount)), 0)).filter(
            and_(
                TokenTransaction.user_id == user_id,
                TokenTransaction.token_type == 'purchased',
                TokenTransaction.source == source,
                TokenTransaction.amount < 0
            )
        ).scalar() or 0
    
    return max(0, credits - debits)


def get_token_transactions(
    db: Session,
    user_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[TokenTransaction]:
    """
    Get token transaction history for a user.
    
    Args:
        db: Database session
        user_id: User ID
        limit: Maximum number of transactions to return
        offset: Number of transactions to skip
    
    Returns:
        List of TokenTransaction objects, ordered by most recent first
    """
    return db.query(TokenTransaction).filter(
        TokenTransaction.user_id == user_id
    ).order_by(
        TokenTransaction.created_at.desc()
    ).offset(offset).limit(limit).all()


def check_token_expiration(db: Session, user_id: str) -> int:
    """
    Check and return count of expired free tokens for a user.
    This is informational - expired tokens are automatically excluded from balance calculations.
    
    Args:
        db: Database session
        user_id: User ID
    
    Returns:
        Number of expired free token transactions
    """
    now = datetime.now(timezone.utc)
    
    expired_count = db.query(func.count(TokenTransaction.id)).filter(
        and_(
            TokenTransaction.user_id == user_id,
            TokenTransaction.token_type == 'free',
            TokenTransaction.amount > 0,
            TokenTransaction.expires_at.isnot(None),
            TokenTransaction.expires_at <= now
        )
    ).scalar() or 0
    
    return expired_count


def has_sufficient_tokens(db: Session, user_id: str, amount: int) -> bool:
    """
    Check if user has sufficient tokens for a transaction.
    
    Args:
        db: Database session
        user_id: User ID
        amount: Number of tokens required
    
    Returns:
        True if user has enough tokens, False otherwise
    """
    balance = calculate_token_balance(db, user_id)
    return balance.total >= amount

