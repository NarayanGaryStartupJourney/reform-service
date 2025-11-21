"""Pydantic schemas for authentication requests and responses."""

from pydantic import BaseModel, EmailStr
from typing import Optional


class SignupRequest(BaseModel):
    """Signup request schema."""
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: str
    full_name: str
    username: Optional[str] = None
    is_verified: bool
    is_pt: bool = False  # Personal Trainer attribute
    technical_level: Optional[str] = None  # beginner, novice, intermediate, advanced, elite
    favorite_exercise: Optional[str] = None  # Favorite exercise
    community_preference: Optional[str] = None  # share_to_similar_levels, share_to_pt, compete_with_someone
    created_at: Optional[str] = None
    tokens_remaining: Optional[int] = None  # Number of tokens remaining today


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""
    current_password: str
    new_password: str


class UpdateUsernameRequest(BaseModel):
    """Update username request schema."""
    username: str


class UpdateProfileRequest(BaseModel):
    """Update user profile attributes request schema."""
    technical_level: Optional[str] = None  # beginner, novice, intermediate, advanced, elite
    favorite_exercise: Optional[str] = None
    community_preference: Optional[str] = None  # share_to_similar_levels, share_to_pt, compete_with_someone

