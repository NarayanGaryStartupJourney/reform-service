"""Contact routes for sending messages to support."""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
from fastapi import APIRouter, HTTPException, status, Depends, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.shared.contact.schemas import ContactRequest, ContactResponse
from src.shared.auth.database import get_db
from src.shared.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/contact", tags=["contact"])
security = HTTPBearer(auto_error=False)

# Rate limiting: track requests by IP address
# In production, consider using Redis or database for distributed rate limiting
rate_limit_store: Dict[str, list] = defaultdict(list)
RATE_LIMIT_MAX_REQUESTS = 3  # Max 3 messages per hour
RATE_LIMIT_WINDOW = timedelta(hours=1)


def get_client_ip(request: Request) -> str:
    """Get client IP address for rate limiting."""
    # Check for forwarded IP (from proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()
    # Fallback to direct connection
    return request.client.host if request.client else "unknown"


def check_rate_limit(ip_address: str) -> bool:
    """Check if IP address has exceeded rate limit."""
    now = datetime.now()
    # Clean old entries
    rate_limit_store[ip_address] = [
        timestamp for timestamp in rate_limit_store[ip_address]
        if now - timestamp < RATE_LIMIT_WINDOW
    ]
    
    # Check if limit exceeded
    if len(rate_limit_store[ip_address]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    
    # Add current request
    rate_limit_store[ip_address].append(now)
    return True


def send_email(name: str, email: str, subject: str, message: str) -> bool:
    """Send email to support@reformgym.fit using SMTP."""
    try:
        # Get email configuration from environment variables
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        support_email = os.environ.get("SUPPORT_EMAIL", "support@reformgym.fit")
        
        if not smtp_user or not smtp_password:
            logging.error("SMTP credentials not configured")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = support_email
        msg['Reply-To'] = email  # Allow support to reply directly to user
        msg['Subject'] = f"Contact Form: {subject}"
        
        # Create email body
        body = f"""
New contact form submission from ReformGym website:

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}

---
This message was sent from the ReformGym contact form.
Reply directly to this email to respond to {name} ({email}).
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()  # Enable encryption
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logging.info(f"Contact form email sent successfully from {email}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send contact form email: {str(e)}", exc_info=True)
        return False


@router.post("/submit", response_model=ContactResponse, status_code=status.HTTP_200_OK)
async def submit_contact_form(
    contact_data: ContactRequest,
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Submit contact form message to support@reformgym.fit.
    
    Features:
    - Rate limiting: Max 3 messages per hour per IP address
    - Input validation and sanitization
    - Secure email sending via SMTP
    - Optional: If user is logged in, their account info is included
    """
    # Rate limiting check
    client_ip = get_client_ip(request)
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please wait before sending another message. (Max {RATE_LIMIT_MAX_REQUESTS} messages per hour)"
        )
    
    # Optional: Get user info if logged in
    user_info = None
    if credentials:
        try:
            # Try to get current user (optional - don't fail if not authenticated)
            user = get_current_user(credentials, db)
            if user:
                user_info = f"User ID: {user.id}, Username: {user.username or 'N/A'}"
        except:
            # User not authenticated or invalid token - that's fine, continue as anonymous
            pass
    
    # Send email
    email_sent = send_email(
        name=contact_data.name,
        email=contact_data.email,
        subject=contact_data.subject,
        message=contact_data.message + (f"\n\n---\n{user_info}" if user_info else "")
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message. Please try again later or contact support directly."
        )
    
    return ContactResponse(
        success=True,
        message="Your message has been sent successfully! We'll get back to you soon."
    )

