"""Pydantic schemas for contact API."""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional


class ContactRequest(BaseModel):
    """Schema for contact form submission."""
    name: str = Field(..., min_length=1, max_length=100, description="Your name")
    email: EmailStr = Field(..., description="Your email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Message subject")
    message: str = Field(..., min_length=10, max_length=2000, description="Your message (10-2000 characters)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Sanitize name input."""
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        # Remove any potentially dangerous characters
        cleaned = v.strip()
        if len(cleaned) < 1:
            raise ValueError("Name must be at least 1 character")
        return cleaned
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        """Sanitize message input."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        cleaned = v.strip()
        if len(cleaned) < 10:
            raise ValueError("Message must be at least 10 characters")
        if len(cleaned) > 2000:
            raise ValueError("Message must be no more than 2000 characters")
        return cleaned


class ContactResponse(BaseModel):
    """Schema for contact form response."""
    success: bool
    message: str

