"""
Landmark validation component - Layer 1 (Foundation)
Validates MediaPipe pose landmarks for single frames and batches
"""

import math


def _is_valid_coordinate(value: float) -> bool:
    """Checks if coordinate value is valid (not NaN, not Infinity, within bounds)."""
    if value is None:
        return False
    if math.isnan(value) or math.isinf(value):
        return False
    return True


def _is_valid_landmark_coords(landmark) -> bool:
    """Validates landmark coordinates are valid numbers."""
    if not hasattr(landmark, 'x') or not hasattr(landmark, 'y'):
        return False
    return _is_valid_coordinate(landmark.x) and _is_valid_coordinate(landmark.y)


def validate_single_landmark(landmark) -> bool:
    """Validates a single landmark exists and has valid coordinates."""
    if landmark is None:
        return False
    return _is_valid_landmark_coords(landmark)


def _check_landmark_exists(landmarks, index: int) -> bool:
    """Checks if landmark at index exists and is accessible."""
    if not landmarks or not hasattr(landmarks, 'landmark'):
        return False
    try:
        landmark = landmarks.landmark[index]
        return validate_single_landmark(landmark)
    except (IndexError, AttributeError):
        return False


def _get_missing_landmarks(landmarks, required: list) -> list:
    """Returns list of missing required landmark indices."""
    missing = []
    for idx in required:
        if not _check_landmark_exists(landmarks, idx):
            missing.append(idx)
    return missing


def _calculate_validation_score(landmarks, required: list) -> float:
    """Calculates validation score (0.0-1.0) based on required landmarks."""
    if not required:
        return 1.0 if landmarks else 0.0
    missing_count = len(_get_missing_landmarks(landmarks, required))
    return max(0.0, 1.0 - (missing_count / len(required)))


def validate_frame_landmarks(landmarks, required_landmarks=None) -> dict:
    """
    Validates a single frame's landmarks.
    Returns validation result with is_valid, missing landmarks, and score.
    """
    has_pose = landmarks is not None and hasattr(landmarks, 'landmark')
    if not has_pose:
        return {
            "is_valid": False,
            "has_pose": False,
            "missing_landmarks": required_landmarks or [],
            "invalid_landmarks": [],
            "validation_score": 0.0,
            "errors": ["No pose detected in frame"],
            "warnings": []
        }
    required = required_landmarks or []
    missing = _get_missing_landmarks(landmarks, required)
    score = _calculate_validation_score(landmarks, required)
    is_valid = len(missing) == 0
    errors = []
    if missing:
        errors.append(f"Missing landmarks: {missing}")
    return {
        "is_valid": is_valid,
        "has_pose": True,
        "missing_landmarks": missing,
        "invalid_landmarks": [],
        "validation_score": score,
        "errors": errors,
        "warnings": []
    }


def validate_landmarks_batch(landmarks_list: list, required_landmarks=None) -> dict:
    """
    Validates multiple frames' landmarks and returns aggregate statistics.
    Returns batch-level validation result with percentages and recommendations.
    """
    if not landmarks_list:
        return {
            "overall_valid": False,
            "valid_frame_count": 0,
            "total_frame_count": 0,
            "valid_frame_percentage": 0.0,
            "per_frame_results": [],
            "missing_critical_frames": [],
            "quality_score": 0.0,
            "errors": ["No landmarks provided"],
            "warnings": [],
            "recommendation": "No video frames to validate"
        }
    per_frame_results = []
    valid_count = 0
    missing_critical = []
    total_score = 0.0
    for i, landmarks in enumerate(landmarks_list):
        frame_result = validate_frame_landmarks(landmarks, required_landmarks)
        per_frame_results.append(frame_result)
        if frame_result["is_valid"]:
            valid_count += 1
        elif required_landmarks:
            missing_critical.append(i)
        total_score += frame_result["validation_score"]
    total_frames = len(landmarks_list)
    valid_percentage = (valid_count / total_frames) if total_frames > 0 else 0.0
    quality_score = (total_score / total_frames) if total_frames > 0 else 0.0
    overall_valid = valid_percentage >= 0.3
    errors = []
    warnings = []
    if valid_percentage < 0.3:
        errors.append(f"Only {valid_percentage:.0%} of frames have valid pose detection")
    elif valid_percentage < 0.7:
        warnings.append(f"Low pose detection quality: {valid_percentage:.0%} of frames valid")
    recommendation = "Ensure person is fully visible throughout video" if not overall_valid else None
    return {
        "overall_valid": overall_valid,
        "valid_frame_count": valid_count,
        "total_frame_count": total_frames,
        "valid_frame_percentage": valid_percentage,
        "per_frame_results": per_frame_results,
        "missing_critical_frames": missing_critical,
        "quality_score": quality_score,
        "errors": errors,
        "warnings": warnings,
        "recommendation": recommendation
    }

