"""Pydantic schemas for social feed API."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PostType(str, Enum):
    """Post type enumeration."""
    SCORE = "score"
    TEXT = "text"
    PLOT = "plot"


class PostCreate(BaseModel):
    """Schema for creating a post."""
    post_type: PostType
    content: Optional[str] = None  # Caption or text post content
    analysis_id: Optional[str] = None  # Link to analysis if sharing from analysis
    score_data: Optional[Dict[str, Any]] = None  # Snapshot of score details
    plot_config: Optional[Dict[str, Any]] = None  # Config to recreate plots


class PostResponse(BaseModel):
    """Schema for post response."""
    id: str
    user_id: str
    username: Optional[str] = None  # Will be populated from user
    user_email: Optional[str] = None  # User's email for badge display
    post_type: str
    content: Optional[str] = None
    analysis_id: Optional[str] = None
    score_data: Optional[Dict[str, Any]] = None
    plot_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    like_count: int = 0
    comment_count: int = 0
    is_liked: bool = False  # Whether current user has liked this post

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    """Schema for creating a comment."""
    content: str = Field(..., min_length=1, max_length=1000)
    parent_comment_id: Optional[str] = None  # For nested replies


class CommentResponse(BaseModel):
    """Schema for comment response."""
    id: str
    post_id: str
    user_id: str
    username: Optional[str] = None  # Will be populated from user
    user_email: Optional[str] = None  # User's email for badge display
    content: str
    parent_comment_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    reply_count: int = 0  # Number of replies (for future nested comments)

    class Config:
        from_attributes = True


class LikeResponse(BaseModel):
    """Schema for like response."""
    post_id: str
    user_id: str
    username: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FollowResponse(BaseModel):
    """Schema for follow response."""
    follower_id: str
    follower_username: Optional[str] = None
    following_id: str
    following_username: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PrivacyUpdate(BaseModel):
    """Schema for updating privacy setting."""
    is_public: bool


class PrivacyResponse(BaseModel):
    """Schema for privacy setting response."""
    is_public: bool


class FeedResponse(BaseModel):
    """Schema for feed response with pagination."""
    posts: List[PostResponse]
    total: int
    limit: int
    offset: int
    has_more: bool

