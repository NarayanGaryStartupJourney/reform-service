"""Database models for analysis history.

This module defines the Analysis model which stores complete video analysis results
for logged-in users. All data needed to recreate scores and plots is preserved.
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from src.shared.auth.database import Base


class Analysis(Base):
    """
    Analysis model - stores complete video analysis results for logged-in users.
    
    Stores all data needed to recreate:
    - Scores: form_analysis contains all component scores and final_score breakdown
    - Plots: calculation_results contains angles_per_frame, asymmetry_per_frame, fps
    - Phase markers: phases contains rep information for plot phase markers
    
    Note: Video files are not stored, only the visualization URL (optional).
    """
    __tablename__ = "analyses"

    # Primary key
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Exercise information
    exercise = Column(Integer, nullable=False, index=True)  # 1=Squat, 2=Bench, 3=Deadlift
    exercise_name = Column(String, nullable=False)  # "Squat", "Bench", "Deadlift"
    
    # Score and metadata
    score = Column(Integer, nullable=False, index=True)  # Final score (0-100)
    frame_count = Column(Integer, nullable=False)
    fps = Column(Float, nullable=False)  # Frames per second - needed for plot recreation (stored as float to preserve precision)
    
    # Analysis data (JSONB for efficient querying and storage)
    calculation_results = Column(JSONB, nullable=False)  # angles_per_frame, asymmetry_per_frame, fps
    form_analysis = Column(JSONB, nullable=False)  # Component scores, final_score breakdown
    camera_angle_info = Column(JSONB, nullable=True)  # Camera angle information
    phases = Column(JSONB, nullable=True)  # Exercise phases (reps) for plot markers
    
    # Video information
    visualization_url = Column(String, nullable=True)  # URL to visualization video
    visualization_filename = Column(String, nullable=True)  # Filename for cleanup
    filename = Column(String, nullable=True)  # Original uploaded filename (not needed for reconstruction)
    file_size = Column(Integer, nullable=False)  # File size in bytes
    
    # Optional user notes
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Composite index for efficient user history queries (most common query)
        Index('idx_analyses_user_created', 'user_id', 'created_at'),
        # Index for filtering by exercise type
        Index('idx_analyses_exercise', 'exercise'),
        # Index for filtering by score range
        Index('idx_analyses_score', 'score'),
        # Composite index for exercise + score queries
        Index('idx_analyses_exercise_score', 'exercise', 'score'),
    )

