"""
Base interface for exercise modules.

All exercise implementations should inherit from this class and implement
all required methods to ensure consistent behavior across exercises.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, Any


class ExerciseBase(ABC):
    """
    Base class for exercise implementations.
    
    Each exercise module (exercise_1, exercise_2, etc.) should implement
    this interface to ensure consistent integration with the analysis pipeline.
    """
    
    @property
    @abstractmethod
    def exercise_id(self) -> int:
        """Return the exercise ID (1, 2, 3, etc.)."""
        pass
    
    @property
    @abstractmethod
    def exercise_name(self) -> str:
        """Return the human-readable exercise name (e.g., 'Squat', 'Bench')."""
        pass
    
    @abstractmethod
    def get_required_landmarks(self) -> Optional[List[int]]:
        """
        Return list of required landmark indices for this exercise.
        
        Returns:
            List of landmark indices, or None if no specific landmarks required.
        """
        pass
    
    @abstractmethod
    def calculate_form(self, landmarks_list: List, validation_result: Optional[Dict] = None) -> Dict:
        """
        Calculate exercise-specific form metrics from pose landmarks.
        
        Args:
            landmarks_list: List of MediaPipe pose landmarks
            validation_result: Optional validation result dict
            
        Returns:
            Dict with structure:
            {
                "exercise": int,
                "angles_per_frame": dict,
                "asymmetry_per_frame": dict,
                ... (exercise-specific fields)
            }
        """
        pass
    
    @abstractmethod
    def detect_phases(self, calculation_results: Dict, fps: float) -> Optional[Dict]:
        """
        Detect exercise phases (reps, active periods, etc.) from calculation results.
        
        Args:
            calculation_results: Results from calculate_form()
            fps: Frames per second
            
        Returns:
            Dict with phase information, or None if not applicable.
            Structure: {"reps": [{"start_frame": int, "end_frame": int, ...}, ...]}
        """
        pass
    
    @abstractmethod
    def analyze_form(self, calculation_results: Dict, phases: Optional[Dict], 
                    fps: float, camera_angle_info: Optional[Dict] = None,
                    landmarks_list: Optional[List] = None, 
                    validation_result: Optional[Dict] = None) -> Optional[Dict]:
        """
        Perform LLM-based form analysis.
        
        Args:
            calculation_results: Results from calculate_form()
            phases: Results from detect_phases()
            fps: Frames per second
            camera_angle_info: Optional camera angle information
            landmarks_list: Optional landmarks for additional analysis
            validation_result: Optional validation result
            
        Returns:
            Dict with form analysis results, or None if not applicable.
            Should include "final_score" with structure:
            {
                "final_score": int,
                "grade": str,
                "component_scores": dict,
                ...
            }
        """
        pass
    
    def get_camera_angle_detector(self) -> Optional[Callable]:
        """
        Return camera angle detection function for this exercise.
        
        Returns:
            Function that takes landmarks_list and returns camera_angle_info dict,
            or None if exercise doesn't use camera angle detection.
        """
        return None
    
    def extract_active_data(self, calculation_results: Dict, phases: Optional[Dict]) -> Dict:
        """
        Extract active data (angles, asymmetry) from exercise phases.
        
        Default implementation extracts all data. Override for exercise-specific logic.
        
        Args:
            calculation_results: Results from calculate_form()
            phases: Results from detect_phases()
            
        Returns:
            Dict with extracted active data (angles, asymmetry, etc.)
        """
        # Default: return all calculation results
        return calculation_results

