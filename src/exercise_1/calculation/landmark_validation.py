"""
Exercise 1 (Squat) landmark validation component - Layer 2
Exercise-specific validation using Layer 1 foundation
"""

from src.shared.pose_estimation.landmark_validation import (
    validate_frame_landmarks,
    validate_landmarks_batch
)


def get_squat_required_landmarks() -> list:
    """
    Returns list of required landmark indices for squat analysis.
    Includes: shoulders, hips, knees, ankles.
    """
    return [11, 12, 23, 24, 25, 26, 27, 28]


def get_squat_critical_landmarks() -> list:
    """
    Returns list of critical landmark indices for squat analysis.
    Critical = must be present for any analysis (hips and knees).
    """
    return [23, 24, 25, 26]


def validate_squat_landmarks(landmarks) -> dict:
    """
    Validates landmarks for squat analysis using Layer 1 validation.
    Returns validation result with squat-specific error messages.
    """
    required = get_squat_required_landmarks()
    result = validate_frame_landmarks(landmarks, required)
    if not result["is_valid"]:
        missing = result["missing_landmarks"]
        critical = get_squat_critical_landmarks()
        missing_critical = [m for m in missing if m in critical]
        if missing_critical:
            result["errors"].append(
                f"Critical landmarks missing for squat: {missing_critical}"
            )
    return result


def validate_squat_landmarks_batch(landmarks_list: list) -> dict:
    """
    Validates batch of landmarks for squat analysis using Layer 1 batch validation.
    Returns batch validation result with squat-specific recommendations.
    """
    required = get_squat_required_landmarks()
    result = validate_landmarks_batch(landmarks_list, required)
    if not result["overall_valid"]:
        result["recommendation"] = (
            "For squat analysis, ensure shoulders, hips, knees, and ankles "
            "are fully visible throughout the video."
        )
    return result

