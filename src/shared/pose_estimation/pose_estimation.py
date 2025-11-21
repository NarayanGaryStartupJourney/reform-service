"""
Pose estimation component - shared across all exercises
Detects body parts and keypoints from video frames
"""

import mediapipe as mp
import cv2
import math


def process_video_streaming_pose(video_path: str, validate: bool = False, required_landmarks: list = None, frame_skip: int = 1) -> tuple:
    """
    Streaming version: Processes frames one at a time from video file.
    Never keeps all frames in memory - processes and discards immediately.
    Returns landmarks list, fps, frame_count, and optionally validation result.
    """
    import cv2
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose()
    results = []
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        pose.close()
        if validate:
            from src.shared.pose_estimation.landmark_validation import validate_landmarks_batch
            validation_result = validate_landmarks_batch([], required_landmarks)
            return [], 30.0, 0, validation_result
        return [], 30.0, 0, None
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    frame_index = 0
    processed_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_index % frame_skip == 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb_frame)
                results.append(result.pose_landmarks)
                processed_count += 1
            
            frame_index += 1
    finally:
        cap.release()
        pose.close()
    
    if frame_skip > 1:
        fps = fps / frame_skip
    
    if validate:
        from src.shared.pose_estimation.landmark_validation import validate_landmarks_batch
        validation_result = validate_landmarks_batch(results, required_landmarks)
        return results, fps, processed_count, validation_result
    
    return results, fps, processed_count, None


def _get_segment_angle(point1, point2) -> float:
    """Calculates angle of segment from vertical. Matches calculation.py logic."""
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


def _get_ankle_segment_angle(point1, point2) -> float:
    """Calculates ankle angle from heel to knee. Matches calculation.py logic."""
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


def _get_status_color(status: str) -> tuple:
    """Returns BGR color tuple for status: good=white, warning=orange, poor=red."""
    if status == "good":
        return (255, 255, 255)
    elif status == "warning":
        return (0, 165, 255)
    elif status == "poor":
        return (0, 0, 255)
    return (255, 255, 255)


def _determine_worse_side_torso(landmarks, frame_status: dict) -> str:
    """Determines which side is worse for torso asymmetry. Returns 'left', 'right', or None."""
    asymmetry_status = frame_status.get("torso_asymmetry")
    if asymmetry_status not in ["warning", "poor"]:
        return None
    
    if (len(landmarks.landmark) <= 24 or
        not all(landmarks.landmark[i] for i in [11, 12, 23, 24])):
        return None
    
    left_angle = _get_segment_angle(landmarks.landmark[23], landmarks.landmark[11])
    right_angle = _get_segment_angle(landmarks.landmark[24], landmarks.landmark[12])
    
    if left_angle is None or right_angle is None:
        return None
    
    asymmetry_value = right_angle - left_angle
    return "right" if asymmetry_value > 0 else "left" if asymmetry_value < 0 else None


def _determine_worse_side_quad(landmarks, frame_status: dict) -> str:
    """Determines which side is worse for quad asymmetry. Returns 'left', 'right', or None."""
    asymmetry_status = frame_status.get("quad_asymmetry")
    if asymmetry_status not in ["warning", "poor"]:
        return None
    
    if (len(landmarks.landmark) <= 26 or
        not all(landmarks.landmark[i] for i in [23, 24, 25, 26])):
        return None
    
    left_angle = _get_segment_angle(landmarks.landmark[23], landmarks.landmark[25])
    right_angle = _get_segment_angle(landmarks.landmark[24], landmarks.landmark[26])
    
    if left_angle is None or right_angle is None:
        return None
    
    asymmetry_value = right_angle - left_angle
    return "right" if asymmetry_value > 0 else "left" if asymmetry_value < 0 else None


def _determine_worse_side_ankle(landmarks, frame_status: dict) -> str:
    """Determines which side is worse for ankle asymmetry. Returns 'left', 'right', or None."""
    asymmetry_status = frame_status.get("ankle_asymmetry")
    if asymmetry_status not in ["warning", "poor"]:
        return None
    
    if (len(landmarks.landmark) <= 30 or
        not all(landmarks.landmark[i] for i in [25, 26, 29, 30])):
        return None
    
    left_angle = _get_ankle_segment_angle(landmarks.landmark[29], landmarks.landmark[25])
    right_angle = _get_ankle_segment_angle(landmarks.landmark[30], landmarks.landmark[26])
    
    if left_angle is None or right_angle is None:
        return None
    
    asymmetry_value = right_angle - left_angle
    return "right" if asymmetry_value > 0 else "left" if asymmetry_value < 0 else None


def _draw_torso_segment(annotated, landmarks, h: int, w: int, frame_status: dict = None):
    """Draws torso segment (shoulder midpoint to hip midpoint) with color-coding."""
    if (len(landmarks.landmark) <= 24 or
        not all(landmarks.landmark[i] for i in [11, 12, 23, 24])):
        return
    
    shoulder_mid_x = int((landmarks.landmark[11].x + landmarks.landmark[12].x) / 2 * w)
    shoulder_mid_y = int((landmarks.landmark[11].y + landmarks.landmark[12].y) / 2 * h)
    hip_mid_x = int((landmarks.landmark[23].x + landmarks.landmark[24].x) / 2 * w)
    hip_mid_y = int((landmarks.landmark[23].y + landmarks.landmark[24].y) / 2 * h)
    
    torso_status = frame_status.get("torso_angle") if frame_status else None
    torso_color = _get_status_color(torso_status)
    
    cv2.line(annotated, (shoulder_mid_x, shoulder_mid_y), (hip_mid_x, hip_mid_y), torso_color, 2)


def _draw_quad_segments(annotated, landmarks, h: int, w: int, frame_status: dict = None):
    """Draws left and right quad segments (hip to knee) with color-coding."""
    quad_status = frame_status.get("quad_angle") if frame_status else None
    quad_color = _get_status_color(quad_status)
    
    if (len(landmarks.landmark) > 25 and
        landmarks.landmark[23] and landmarks.landmark[25]):
        left_hip_x = int(landmarks.landmark[23].x * w)
        left_hip_y = int(landmarks.landmark[23].y * h)
        left_knee_x = int(landmarks.landmark[25].x * w)
        left_knee_y = int(landmarks.landmark[25].y * h)
        cv2.line(annotated, (left_hip_x, left_hip_y), (left_knee_x, left_knee_y), quad_color, 2)
    
    if (len(landmarks.landmark) > 26 and
        landmarks.landmark[24] and landmarks.landmark[26]):
        right_hip_x = int(landmarks.landmark[24].x * w)
        right_hip_y = int(landmarks.landmark[24].y * h)
        right_knee_x = int(landmarks.landmark[26].x * w)
        right_knee_y = int(landmarks.landmark[26].y * h)
        cv2.line(annotated, (right_hip_x, right_hip_y), (right_knee_x, right_knee_y), quad_color, 2)


def _get_landmark_colors(landmarks, frame_status: dict, landmark_indices: list) -> dict:
    """Returns color dict for each landmark index based on asymmetry status."""
    colors = {}
    default_green = (0, 255, 0)
    
    for idx in landmark_indices:
        colors[idx] = default_green
    
    if not frame_status:
        return colors
    
    worse_torso_side = _determine_worse_side_torso(landmarks, frame_status)
    worse_quad_side = _determine_worse_side_quad(landmarks, frame_status)
    worse_ankle_side = _determine_worse_side_ankle(landmarks, frame_status)
    
    torso_status = frame_status.get("torso_asymmetry")
    quad_status = frame_status.get("quad_asymmetry")
    ankle_status = frame_status.get("ankle_asymmetry")
    
    if worse_torso_side and torso_status in ["warning", "poor"]:
        color = _get_status_color(torso_status)
        if worse_torso_side == "left":
            colors[11] = color
        else:
            colors[12] = color
    
    if worse_quad_side and quad_status in ["warning", "poor"]:
        color = _get_status_color(quad_status)
        if worse_quad_side == "left":
            colors[25] = color
        else:
            colors[26] = color
    
    if worse_ankle_side and ankle_status in ["warning", "poor"]:
        color = _get_status_color(ankle_status)
        if worse_ankle_side == "left":
            colors[29] = color
        else:
            colors[30] = color
    
    return colors


def create_visualization_streaming(video_path: str, landmarks_list: list, output_path: str,
                                   landmark_indices: list, per_frame_status: dict = None, 
                                   fps: float = 30.0, frame_skip: int = 1) -> str:
    """
    Streaming version: Reads frames from video, draws landmarks, writes directly to output video.
    Uses imageio-ffmpeg to create browser-compatible H.264 MP4 files.
    Never keeps all frames in memory - processes one frame at a time.
    
    Args:
        video_path: Path to input video file
        landmarks_list: List of MediaPipe pose landmarks (must match processed frames)
        output_path: Path to output video file (should be .mp4)
        landmark_indices: List of landmark indices to draw
        per_frame_status: Optional dict mapping frame index to status dict
        fps: Frames per second for output video
        frame_skip: Frame skip factor (must match the one used for pose estimation)
    
    Returns:
        Path to output video file
    """
    import imageio
    import os
    
    # Ensure output path is .mp4 for browser compatibility
    if not output_path.endswith('.mp4'):
        base_path = os.path.splitext(output_path)[0]
        output_path = f"{base_path}.mp4"
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Calculate padded dimensions (divisible by 16 to avoid imageio-ffmpeg resizing warning)
    MACRO_BLOCK_SIZE = 16
    padded_width = ((width + MACRO_BLOCK_SIZE - 1) // MACRO_BLOCK_SIZE) * MACRO_BLOCK_SIZE
    padded_height = ((height + MACRO_BLOCK_SIZE - 1) // MACRO_BLOCK_SIZE) * MACRO_BLOCK_SIZE
    
    # Only pad if dimensions need adjustment
    needs_padding = (padded_width != width) or (padded_height != height)
    
    # Create video writer using imageio-ffmpeg (H.264 codec, browser-compatible)
    # Frames will be padded to dimensions divisible by 16 before writing
    try:
        writer = imageio.get_writer(
            output_path,
            fps=fps,
            codec='libx264',  # H.264 codec for browser compatibility
            quality=8,  # Good quality (0-10 scale, 8 is high quality)
            pixelformat='yuv420p'  # Ensures browser compatibility
        )
    except Exception as e:
        cap.release()
        raise ValueError(f"Could not create video writer: {str(e)}")
    
    frame_index = 0
    landmark_index = 0
    frames_written = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_index % frame_skip == 0:
                if landmark_index >= len(landmarks_list):
                    break
                
                annotated = frame.copy()
                landmarks = landmarks_list[landmark_index]
                
                if landmarks:
                    h, w, _ = frame.shape
                    frame_status = per_frame_status.get(landmark_index) if per_frame_status else None
                    
                    _draw_torso_segment(annotated, landmarks, h, w, frame_status)
                    _draw_quad_segments(annotated, landmarks, h, w, frame_status)
                    
                    colors = _get_landmark_colors(landmarks, frame_status, landmark_indices)
                    
                    for idx in landmark_indices:
                        if idx < len(landmarks.landmark) and landmarks.landmark[idx]:
                            lm = landmarks.landmark[idx]
                            x, y = int(lm.x * w), int(lm.y * h)
                            cv2.circle(annotated, (x, y), 5, colors.get(idx, (0, 255, 0)), -1)
                
                # Pad frame to be divisible by 16 if needed
                if needs_padding:
                    # Add black padding to right and bottom edges
                    annotated = cv2.copyMakeBorder(
                        annotated,
                        0,  # top
                        padded_height - height,  # bottom
                        0,  # left
                        padded_width - width,  # right
                        cv2.BORDER_CONSTANT,
                        value=[0, 0, 0]  # black padding
                    )
                
                rgb_frame = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                
                try:
                    writer.append_data(rgb_frame)
                    frames_written += 1
                except Exception as e:
                    import warnings
                    warnings.warn(f"Failed to write frame {landmark_index} to video: {str(e)}")
                
                landmark_index += 1
            
            frame_index += 1
    finally:
        cap.release()
        writer.close()
    
    if not os.path.exists(output_path):
        raise ValueError(f"Output video file was not created: {output_path}")
    
    file_size = os.path.getsize(output_path)
    if file_size == 0:
        raise ValueError(f"Output video file is empty: {output_path} (wrote {frames_written} frames)")
    
    test_cap = cv2.VideoCapture(output_path)
    if not test_cap.isOpened():
        raise ValueError(f"Output video file cannot be opened: {output_path}")
    
    ret, test_frame = test_cap.read()
    test_cap.release()
    if not ret or test_frame is None:
        raise ValueError(f"Output video file appears corrupted: {output_path} (cannot read frames)")
    
    return output_path


