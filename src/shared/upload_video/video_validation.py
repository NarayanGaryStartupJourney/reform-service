"""
Video validation component
Validates video format, codec, and quality
"""

import cv2
import numpy as np
import os


def get_video_magic_numbers() -> dict:
    """
    Returns dictionary of video file magic numbers (file signatures).
    Key: format name, Value: list of byte signatures (as bytes or hex strings)
    """
    return {
        'mp4': [
            b'\x00\x00\x00\x20ftyp',  # MP4 (ISO Base Media)
            b'\x00\x00\x00\x18ftyp',  # MP4 variant
            b'\x00\x00\x00\x1Cftyp',  # MP4 variant
            b'\x00\x00\x00\x1Cftypisom',  # MP4 (ISO Media)
            b'\x00\x00\x00\x1Cftypmp41',  # MP4 (MPEG-4 v1)
            b'\x00\x00\x00\x1Cftypmp42',  # MP4 (MPEG-4 v2)
            b'\x00\x00\x00\x1Cftypavc1',  # MP4 (AVC)
            b'\x00\x00\x00\x1Cftypiso2',  # MP4 (ISO 20022)
        ],
        'mov': [
            b'\x00\x00\x00\x20ftypqt  ',  # QuickTime
            b'\x00\x00\x00\x14ftypqt  ',  # QuickTime variant
            b'\x00\x00\x00\x18ftypqt  ',  # QuickTime variant
            b'\x00\x00\x00\x1Cftypqt  ',  # QuickTime variant
        ],
        'avi': [
            b'RIFF',  # AVI (starts with RIFF, then has AVI at offset 8)
        ],
        'webm': [
            b'\x1A\x45\xDF\xA3',  # WebM (EBML header)
        ],
        'mkv': [
            b'\x1A\x45\xDF\xA3',  # Matroska (same as WebM)
        ],
        'flv': [
            b'FLV',  # Flash Video
        ],
        '3gp': [
            b'\x00\x00\x00\x20ftyp3g2a',  # 3GP
            b'\x00\x00\x00\x20ftyp3gp4',  # 3GP variant
            b'\x00\x00\x00\x20ftyp3gp5',  # 3GP variant
        ],
    }


def validate_file_headers(file_path: str) -> dict:
    """
    Validates file headers (magic numbers) to ensure file is actually a video.
    Returns validation result with detected format and errors.
    """
    if not os.path.exists(file_path):
        return {
            "is_valid": False,
            "detected_format": None,
            "errors": ["File does not exist."],
            "recommendation": "File may have been deleted or path is incorrect."
        }
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(32)
    except Exception as e:
        return {
            "is_valid": False,
            "detected_format": None,
            "errors": [f"Cannot read file headers: {str(e)}"],
            "recommendation": "File may be corrupted or inaccessible."
        }
    
    if len(header) < 12:
        return {
            "is_valid": False,
            "detected_format": None,
            "errors": ["File is too small to contain valid video headers."],
            "recommendation": "File appears to be corrupted or not a valid video file."
        }
    
    magic_numbers = get_video_magic_numbers()
    detected_format = None
    
    for format_name, signatures in magic_numbers.items():
        for signature in signatures:
            if format_name == 'avi':
                if header.startswith(b'RIFF') and len(header) >= 12:
                    if header[8:12] == b'AVI ' or header[8:12] == b'AVIX':
                        detected_format = format_name
                        break
            elif format_name == 'flv':
                if header.startswith(signature):
                    detected_format = format_name
                    break
            else:
                if header.startswith(signature):
                    detected_format = format_name
                    break
        if detected_format:
            break
    
    if detected_format:
        return {
            "is_valid": True,
            "detected_format": detected_format,
            "errors": [],
            "warnings": [],
            "recommendation": None
        }
    else:
        hex_header = header[:16].hex()
        return {
            "is_valid": False,
            "detected_format": None,
            "errors": [f"File headers do not match any known video format. Header: {hex_header}"],
            "recommendation": "File may not be a valid video file, or format is not supported. Please use MP4, MOV, AVI, or WebM format."
        }


def get_supported_codecs() -> list:
    """
    Returns whitelist of supported video codecs.
    These are codecs that OpenCV/FFmpeg reliably supports.
    Note: If OpenCV can read frames, video will be accepted even if codec is not in this list.
    """
    return ['avc1', 'h264', 'H264', 'X264', 'mp4v', 'MP4V', 'hevc', 'HEVC', 'hvc1', 'HVC1']


def _fourcc_to_string(fourcc_int: float) -> str:
    """Converts FOURCC integer to string representation."""
    if fourcc_int == 0 or fourcc_int is None:
        return "unknown"
    fourcc_int = int(fourcc_int)
    fourcc_str = "".join([chr(int((fourcc_int >> (8 * i)) & 0xFF)) for i in range(4)])
    return fourcc_str.strip('\x00')


def validate_file_content(video_path: str) -> dict:
    """
    Validates that the file is actually a valid, processable video file.
    Checks that OpenCV can open it, read frames, and the file structure is valid.
    Returns validation result with detailed information.
    """
    if not os.path.exists(video_path):
        return {
            "is_valid": False,
            "errors": ["File does not exist."],
            "recommendation": "File may have been deleted or path is incorrect."
        }
    
    file_size = os.path.getsize(video_path)
    if file_size == 0:
        return {
            "is_valid": False,
            "errors": ["File is empty."],
            "recommendation": "Please upload a valid video file."
        }
    
    if file_size < 1024:
        return {
            "is_valid": False,
            "errors": ["File is too small to be a valid video (less than 1KB)."],
            "recommendation": "File appears to be corrupted or not a valid video file."
        }
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {
            "is_valid": False,
            "errors": ["OpenCV cannot open the video file."],
            "recommendation": "File may be corrupted or in an unsupported format. Please convert to MP4 (H.264) format."
        }
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Validate properties
    errors = []
    warnings = []
    
    if fps <= 0 or fps > 1000:
        errors.append(f"Invalid FPS detected: {fps}. Video may be corrupted.")
    
    if frame_count <= 0:
        errors.append("Video has no frames. File may be corrupted.")
    
    if width <= 0 or height <= 0:
        errors.append(f"Invalid video dimensions: {width}x{height}. Video may be corrupted.")
    
    if width > 10000 or height > 10000:
        warnings.append(f"Unusually large video dimensions: {width}x{height}. Processing may be slow.")
    
    # Try to read at least one frame
    frames_read = 0
    valid_frames = 0
    test_frames = min(10, frame_count) if frame_count > 0 else 10
    
    for i in range(test_frames):
        ret, frame = cap.read()
        frames_read += 1
        if ret and frame is not None:
            valid_frames += 1
            # Check frame validity
            if frame.shape[0] != height or frame.shape[1] != width:
                warnings.append(f"Frame {i} has inconsistent dimensions.")
        else:
            break
    
    cap.release()
    
    if valid_frames == 0:
        errors.append("Cannot read any frames from video. File may be corrupted or incomplete.")
    
    if valid_frames < test_frames and frame_count > test_frames:
        warnings.append(f"Only {valid_frames}/{test_frames} test frames could be read. Video may be partially corrupted.")
    
    if errors:
        return {
            "is_valid": False,
            "errors": errors,
            "warnings": warnings,
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "valid_frames_read": valid_frames,
            "recommendation": "File appears to be corrupted or invalid. Please try a different video file or re-export the video."
        }
    
    return {
        "is_valid": True,
        "errors": [],
        "warnings": warnings,
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "valid_frames_read": valid_frames,
        "recommendation": None
    }


def validate_video_format(video_path: str) -> dict:
    """
    Validates video format and codec using whitelist approach.
    If OpenCV can open and read frames, allows the video even if codec is not whitelisted.
    Returns validation result with codec info and errors.
    """
    supported_codecs = get_supported_codecs()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {
            "is_valid": False,
            "codec": "unknown",
            "can_open": False,
            "errors": ["Video file cannot be opened. Format may not be supported."],
            "recommendation": "Please convert to MP4 (H.264) format using a video converter."
        }
    
    fourcc_int = cap.get(cv2.CAP_PROP_FOURCC)
    codec = _fourcc_to_string(fourcc_int)
    
    ret, test_frame = cap.read()
    can_read_frames = ret and test_frame is not None
    cap.release()
    
    is_codec_whitelisted = codec.lower() in [c.lower() for c in supported_codecs]
    
    if can_read_frames:
        if not is_codec_whitelisted and codec != "unknown":
            return {
                "is_valid": True,
                "codec": codec,
                "can_open": True,
                "can_read_frames": True,
                "errors": [],
                "warnings": [f"Video codec '{codec}' is not in whitelist, but OpenCV can read frames. Proceeding with caution."],
                "recommendation": "For best compatibility, consider converting to MP4 (H.264) format."
            }
        elif codec == "unknown":
            return {
                "is_valid": True,
                "codec": "unknown",
                "can_open": True,
                "can_read_frames": True,
                "errors": [],
                "warnings": ["Could not detect video codec, but OpenCV can read frames. Proceeding."],
                "recommendation": None
            }
        else:
            return {
                "is_valid": True,
                "codec": codec,
                "can_open": True,
                "can_read_frames": True,
                "errors": [],
                "warnings": [],
                "recommendation": None
            }
    else:
        errors = []
        if not is_codec_whitelisted and codec != "unknown":
            errors.append(f"Video codec '{codec}' is not supported and OpenCV cannot read frames.")
        elif codec == "unknown":
            errors.append("Could not detect video codec and OpenCV cannot read frames.")
        else:
            errors.append("OpenCV cannot read frames from video file.")
        return {
            "is_valid": False,
            "codec": codec,
            "can_open": True,
            "can_read_frames": False,
            "errors": errors,
            "recommendation": "Please convert to MP4 (H.264) format for best compatibility."
        }


def _is_valid_frame_dimensions(frame) -> bool:
    """Checks if frame has valid dimensions."""
    if frame is None:
        return False
    if not hasattr(frame, 'shape') or len(frame.shape) < 2:
        return False
    h, w = frame.shape[0], frame.shape[1]
    return h > 0 and w > 0 and h <= 10000 and w <= 10000


def _is_corrupted_frame(frame) -> bool:
    """Checks if frame appears corrupted (all black, all white, invalid)."""
    if not _is_valid_frame_dimensions(frame):
        return True
    if len(frame.shape) == 3:
        mean_val = np.mean(frame)
        if mean_val < 1.0 or mean_val > 254.0:
            return True
    return False


def validate_extracted_frames(frames: list) -> dict:
    """
    Validates extracted frames for quality and corruption.
    Returns validation result with frame count and errors.
    """
    if not frames:
        return {
            "is_valid": False,
            "frame_count": 0,
            "errors": ["No frames extracted from video."],
            "recommendation": "Video file may be corrupted or format not fully supported. Please try re-exporting the video."
        }
    valid_frames = []
    corrupted_count = 0
    for i, frame in enumerate(frames):
        if not _is_valid_frame_dimensions(frame):
            corrupted_count += 1
            continue
        if _is_corrupted_frame(frame):
            corrupted_count += 1
            continue
        valid_frames.append(frame)
    if len(valid_frames) == 0:
        return {
            "is_valid": False,
            "frame_count": len(frames),
            "valid_frame_count": 0,
            "corrupted_count": corrupted_count,
            "errors": ["All extracted frames are invalid or corrupted."],
            "recommendation": "Video file appears corrupted. Please try a different video file or re-export the video."
        }
    if corrupted_count > len(frames) * 0.5:
        return {
            "is_valid": False,
            "frame_count": len(frames),
            "valid_frame_count": len(valid_frames),
            "corrupted_count": corrupted_count,
            "errors": [f"More than 50% of frames are corrupted ({corrupted_count}/{len(frames)})."],
            "recommendation": "Video file appears heavily corrupted. Please try a different video file."
        }
    return {
        "is_valid": True,
        "frame_count": len(frames),
        "valid_frame_count": len(valid_frames),
        "corrupted_count": corrupted_count,
        "errors": [],
        "recommendation": None
    }


def validate_fps(fps: float) -> dict:
    """
    Validates FPS value. Reusable for both upload and livestream modes.
    Returns validation result with errors and warnings.
    """
    if fps is None:
        return {
            "is_valid": False,
            "fps": None,
            "errors": ["FPS is missing or None."],
            "warnings": [],
            "recommendation": "FPS metadata may be corrupted. Using default 30.0 fps."
        }
    if not isinstance(fps, (int, float)):
        return {
            "is_valid": False,
            "fps": fps,
            "errors": [f"Invalid FPS type: {type(fps)}. Expected number."],
            "warnings": [],
            "recommendation": "FPS metadata may be corrupted."
        }
    if fps <= 0:
        return {
            "is_valid": False,
            "fps": fps,
            "errors": [f"Invalid FPS: {fps}. FPS must be greater than 0."],
            "warnings": [],
            "recommendation": "FPS metadata appears corrupted. Please re-export the video."
        }
    if fps < 15:
        return {
            "is_valid": False,
            "fps": fps,
            "errors": [f"FPS too low: {fps} fps. Minimum: 15 fps."],
            "warnings": [],
            "recommendation": "Video FPS is too low for accurate analysis. Please use a video with at least 15 fps."
        }
    if fps > 120:
        return {
            "is_valid": False,
            "fps": fps,
            "errors": [f"FPS too high: {fps} fps. Maximum: 120 fps."],
            "warnings": [],
            "recommendation": "FPS appears unusually high. Video metadata may be corrupted."
        }
    warnings = []
    if fps < 20 or fps > 60:
        warnings.append(f"Unusual FPS detected: {fps} fps. Results may be less accurate.")
    return {
        "is_valid": True,
        "fps": fps,
        "errors": [],
        "warnings": warnings,
        "recommendation": None
    }


def detect_fps_from_video(video_path: str, frame_count: int = None) -> tuple:
    """
    Detects FPS from video metadata. Upload mode only.
    Returns tuple of (fps, validation_result).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        validation = validate_fps(None)
        return 30.0, validation
    fps_metadata = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if fps_metadata and fps_metadata > 0:
        fps = fps_metadata
        validation = validate_fps(fps)
    else:
        fps = 30.0
        validation = validate_fps(fps)
        validation["warnings"].append("FPS metadata missing or invalid. Using default 30.0 fps.")
        validation["is_valid"] = True
    return fps, validation


def validate_video_duration(frame_count: int, fps: float, max_duration_seconds: float = 120.0) -> dict:
    """
    Validates video duration based on frame count and FPS.
    Returns validation result with errors and duration info.
    """
    if frame_count is None or frame_count <= 0:
        return {
            "is_valid": False,
            "duration_seconds": None,
            "frame_count": frame_count,
            "fps": fps,
            "errors": ["Invalid frame count. Cannot calculate duration."],
            "recommendation": "Video file may be corrupted or empty."
        }
    if fps is None or fps <= 0:
        return {
            "is_valid": False,
            "duration_seconds": None,
            "frame_count": frame_count,
            "fps": fps,
            "errors": ["Invalid FPS. Cannot calculate duration."],
            "recommendation": "FPS metadata may be corrupted."
        }
    duration_seconds = frame_count / fps
    if duration_seconds > max_duration_seconds:
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        max_minutes = int(max_duration_seconds // 60)
        max_seconds = int(max_duration_seconds % 60)
        return {
            "is_valid": False,
            "duration_seconds": duration_seconds,
            "frame_count": frame_count,
            "fps": fps,
            "errors": [f"Video too long ({minutes}:{seconds:02d}). Maximum duration: {max_minutes}:{max_seconds:02d} ({max_duration_seconds} seconds)."],
            "recommendation": f"Please select a video shorter than {max_duration_seconds} seconds (2 minutes)."
        }
    return {
        "is_valid": True,
        "duration_seconds": duration_seconds,
        "frame_count": frame_count,
        "fps": fps,
        "errors": [],
        "recommendation": None
    }

