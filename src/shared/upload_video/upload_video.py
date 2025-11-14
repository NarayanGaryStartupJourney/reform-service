"""
Receives and processes uploaded video files from frontend
Extracts frames from uploaded video for processing
"""

import tempfile
import os
from fastapi import UploadFile
import cv2


def accept_video_file(file: UploadFile) -> dict:
    """
    Accepts and validates video file from FormData upload
    Returns file metadata if valid
    """
    if not file.content_type or not file.content_type.startswith('video/'):
        raise ValueError("File must be a video")
    
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "file": file
    }


def save_video_temp(file: UploadFile) -> str:
    """
    Saves uploaded video file to temporary location
    Returns path to temporary file
    """
    file.file.seek(0)
    suffix = os.path.splitext(file.filename)[1] if file.filename else '.mp4'
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    content = file.file.read()
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


def extract_frames(video_path: str) -> list:
    """
    Extracts frames from video file using OpenCV
    Returns list of frames as numpy arrays
    """
    cap = cv2.VideoCapture(video_path)
    frames = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    
    cap.release()
    return frames

