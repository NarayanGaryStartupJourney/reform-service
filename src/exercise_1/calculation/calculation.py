"""
Exercise 1 calculation component
Uses pose estimation data points to determine form correctness
"""

import math


def get_segment_angle(point1, point2) -> float:
    """Calculates angle of segment from vertical. Returns angle in degrees (0 when upright, 90 when bent forward)."""
    dx = point2.x - point1.x
    dy = point2.y - point1.y
    angle_from_horizontal = math.degrees(math.atan2(-dy, dx))
    if angle_from_horizontal < 0:
        angle_from_horizontal += 360
    if angle_from_horizontal <= 90:
        return 90 - angle_from_horizontal
    elif angle_from_horizontal <= 180:
        return angle_from_horizontal - 90
    elif angle_from_horizontal <= 270:
        return 270 - angle_from_horizontal
    else:
        return angle_from_horizontal - 270


def calculate_torso_angle_per_frame(landmarks_list: list) -> list:
    """Calculates torso angle for each frame."""
    if not landmarks_list:
        return []
    angles = []
    for landmarks in landmarks_list:
        if not landmarks:
            angles.append(None)
            continue
        left_angle = get_segment_angle(landmarks.landmark[23], landmarks.landmark[11])
        right_angle = get_segment_angle(landmarks.landmark[24], landmarks.landmark[12])
        if left_angle is not None and right_angle is not None:
            angles.append((left_angle + right_angle) / 2)
        else:
            angles.append(None)
    return angles


def calculate_quad_angle_per_frame(landmarks_list: list) -> list:
    """Calculates quad angle for each frame."""
    if not landmarks_list:
        return []
    angles = []
    for landmarks in landmarks_list:
        if not landmarks:
            angles.append(None)
            continue
        left_angle = get_segment_angle(landmarks.landmark[23], landmarks.landmark[25])
        right_angle = get_segment_angle(landmarks.landmark[24], landmarks.landmark[26])
        if left_angle is not None and right_angle is not None:
            angles.append((left_angle + right_angle) / 2)
        else:
            angles.append(None)
    return angles


def get_ankle_segment_angle(point1, point2) -> float:
    """Calculates angle of heel-knee segment. Returns angle in degrees (90 when upright, < 90 when knee forward)."""
    dx = point2.x - point1.x
    dy = point2.y - point1.y
    angle_from_horizontal = math.degrees(math.atan2(-dy, dx))
    if angle_from_horizontal < 0:
        angle_from_horizontal += 360
    if angle_from_horizontal <= 90:
        return angle_from_horizontal
    elif angle_from_horizontal <= 180:
        return 180 - angle_from_horizontal
    elif angle_from_horizontal <= 270:
        return 270 - angle_from_horizontal
    else:
        return 360 - angle_from_horizontal


def calculate_ankle_angle_per_frame(landmarks_list: list) -> list:
    """Calculates ankle angle for each frame from heel-knee segments."""
    if not landmarks_list:
        return []
    angles = []
    for landmarks in landmarks_list:
        if not landmarks:
            angles.append(None)
            continue
        left_angle = get_ankle_segment_angle(landmarks.landmark[29], landmarks.landmark[25])
        right_angle = get_ankle_segment_angle(landmarks.landmark[30], landmarks.landmark[26])
        if left_angle is not None and right_angle is not None:
            angles.append((left_angle + right_angle) / 2)
        else:
            angles.append(None)
    return angles


def calculate_squat_form(landmarks_list: list) -> dict:
    """Calculates squat form metrics from pose landmarks. Returns per-frame angles."""
    torso_angles_per_frame = calculate_torso_angle_per_frame(landmarks_list)
    quad_angles_per_frame = calculate_quad_angle_per_frame(landmarks_list)
    ankle_angles_per_frame = calculate_ankle_angle_per_frame(landmarks_list)
    return {
        "exercise": 1,
        "angles_per_frame": {
            "torso_angle": torso_angles_per_frame,
            "quad_angle": quad_angles_per_frame,
            "ankle_angle": ankle_angles_per_frame
        }
    }
