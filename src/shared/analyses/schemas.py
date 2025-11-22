"""Pydantic schemas for analysis API.

This module defines request/response schemas for the analysis history API endpoints.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class AnalysisResponse(BaseModel):
    """Schema for single analysis response with full details."""
    id: str
    user_id: str
    exercise: int
    exercise_name: str
    score: int
    frame_count: int
    fps: float  # Float to preserve precision (e.g., 29.97 fps)
    calculation_results: Dict[str, Any]  # Contains angles_per_frame, asymmetry_per_frame, fps
    form_analysis: Dict[str, Any]  # Contains all component scores and final_score breakdown
    camera_angle_info: Optional[Dict[str, Any]] = None
    phases: Optional[Dict[str, Any]] = None  # Rep phases for plot markers
    visualization_url: Optional[str] = None
    visualization_filename: Optional[str] = None
    file_size: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.replace(microsecond=0).isoformat() if v else None
        }


class AnalysisListItem(BaseModel):
    """Schema for analysis list item (summary without full data)."""
    id: str
    exercise: int
    exercise_name: str
    score: int
    frame_count: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.replace(microsecond=0).isoformat() if v else None
        }


class AnalysisListResponse(BaseModel):
    """Schema for analysis list response."""
    analyses: List[AnalysisListItem]
    total: int
    limit: int
    offset: int


class UpdateNotesRequest(BaseModel):
    """Schema for updating analysis notes."""
    notes: Optional[str] = None


class ProgressMetrics(BaseModel):
    """Schema for progress metrics/trends."""
    total_analyses: int
    average_score: Optional[float] = None
    best_score: Optional[int] = None
    worst_score: Optional[int] = None
    score_trend: List[Dict[str, Any]]  # List of {date, score, exercise} - one point per day per exercise (averaged if multiple on same day)
    analyses_by_exercise: Dict[str, int]  # Count of analyses per exercise
    recent_analyses: List[AnalysisListItem]  # Last 5 analyses

