"""
Rate limiting utilities for authentication endpoints.
Simple in-memory rate limiting that can be upgraded to Redis later.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock
from fastapi import HTTPException, status
from typing import Dict, Deque
import time

# Rate limit stores: {ip_address: deque of timestamps}
_rate_limit_stores: Dict[str, Dict[str, Deque[float]]] = defaultdict(lambda: defaultdict(deque))
_rate_limit_locks: Dict[str, Lock] = defaultdict(Lock)


def check_rate_limit(
    identifier: str,
    limit_name: str,
    max_requests: int,
    window_seconds: int
) -> None:
    """
    Check if identifier has exceeded rate limit.
    
    Args:
        identifier: IP address or user identifier
        limit_name: Name of the rate limit (e.g., 'login', 'signup')
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
    
    Raises:
        HTTPException with 429 status if rate limit exceeded
    """
    now = time.time()
    lock = _rate_limit_locks[limit_name]
    store = _rate_limit_stores[limit_name][identifier]
    
    with lock:
        # Remove old entries outside the window
        while store and store[0] <= now - window_seconds:
            store.popleft()
        
        # Check if limit exceeded
        if len(store) >= max_requests:
            retry_after = int(store[0] + window_seconds - now) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded: {max_requests} requests per {window_seconds} seconds",
                    "retry_after_seconds": max(retry_after, 1)
                }
            )
        
        # Record this request
        store.append(now)
        
        # Clean up empty stores periodically (every 1000 requests)
        if len(store) == 0 and len(_rate_limit_stores[limit_name]) > 1000:
            _rate_limit_stores[limit_name].pop(identifier, None)


def get_client_ip(request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

