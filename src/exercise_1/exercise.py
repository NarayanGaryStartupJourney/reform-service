"""
Exercise 1 (Squat) implementation.
Wraps existing exercise_1 modules to implement ExerciseBase interface.
"""

from typing import List, Dict, Optional, Callable
from src.shared.exercises.base import ExerciseBase
from src.exercise_1.calculation.calculation import calculate_squat_form, detect_camera_angle
from src.exercise_1.calculation.landmark_validation import get_squat_required_landmarks
from src.exercise_1.llm_form_analysis.llm_form_analysis import (
    detect_squat_phases,
    analyze_torso_angle,
    analyze_quad_angle,
    analyze_ankle_angle,
    analyze_asymmetry,
    analyze_rep_consistency,
    analyze_glute_dominance,
    analyze_knee_valgus,
    calculate_final_score,
    _is_front_view
)


class Exercise1(ExerciseBase):
    """Exercise 1: Squat implementation."""
    
    @property
    def exercise_id(self) -> int:
        return 1
    
    @property
    def exercise_name(self) -> str:
        return "Squat"
    
    def get_required_landmarks(self) -> Optional[List[int]]:
        """Return required landmarks for squat analysis."""
        return get_squat_required_landmarks()
    
    def calculate_form(self, landmarks_list: List, validation_result: Optional[Dict] = None) -> Dict:
        """Calculate squat form metrics from pose landmarks."""
        return calculate_squat_form(landmarks_list, validation_result)
    
    def detect_phases(self, calculation_results: Dict, fps: float) -> Optional[Dict]:
        """Detect squat phases (reps) from calculation results."""
        if not calculation_results.get("angles_per_frame"):
            return None
        
        quad_angles_raw = calculation_results["angles_per_frame"].get("quad_angle", [])
        if not quad_angles_raw:
            return None
        
        return detect_squat_phases(quad_angles_raw, fps)
    
    def analyze_form(self, calculation_results: Dict, phases: Optional[Dict], 
                    fps: float, camera_angle_info: Optional[Dict] = None,
                    landmarks_list: Optional[List] = None, 
                    validation_result: Optional[Dict] = None) -> Optional[Dict]:
        """Perform LLM-based squat form analysis."""
        if not calculation_results.get("angles_per_frame"):
            return None
        
        # Extract active data from phases
        quad_angles_raw = calculation_results["angles_per_frame"].get("quad_angle", [])
        torso_angles_raw = calculation_results["angles_per_frame"].get("torso_angle", [])
        
        if not phases or not phases.get("reps"):
            return None
        
        # Extract active angles and asymmetry from phases
        quad_angles = self._extract_active_angles(quad_angles_raw, phases)
        ankle_angles = self._extract_active_angles(
            calculation_results["angles_per_frame"].get("ankle_angle", []), phases
        )
        asymmetry_data = calculation_results.get("asymmetry_per_frame", {})
        torso_asymmetry = self._extract_active_angles(
            asymmetry_data.get("torso_asymmetry", []), phases
        )
        quad_asymmetry = self._extract_active_angles(
            asymmetry_data.get("quad_asymmetry", []), phases
        )
        ankle_asymmetry = self._extract_active_angles(
            asymmetry_data.get("ankle_asymmetry", []), phases
        )
        
        # Perform analyses
        torso_analysis = analyze_torso_angle(torso_angles_raw, quad_angles_raw, validation_result)
        quad_analysis = analyze_quad_angle(quad_angles)
        ankle_analysis = analyze_ankle_angle(ankle_angles)
        torso_asymmetry_analysis = analyze_asymmetry(torso_asymmetry, "torso")
        quad_asymmetry_analysis = analyze_asymmetry(quad_asymmetry, "quad")
        ankle_asymmetry_analysis = analyze_asymmetry(ankle_asymmetry, "ankle")
        
        result = {
            "torso_angle": torso_analysis,
            "quad_angle": quad_analysis,
            "ankle_angle": ankle_analysis,
            "torso_asymmetry": torso_asymmetry_analysis,
            "quad_asymmetry": quad_asymmetry_analysis,
            "ankle_asymmetry": ankle_asymmetry_analysis
        }
        
        # Optional analyses
        rep_consistency = analyze_rep_consistency(
            calculation_results["angles_per_frame"],
            asymmetry_data,
            phases.get("reps", [])
        )
        if rep_consistency:
            result["rep_consistency"] = rep_consistency
        
        glute_dominance = analyze_glute_dominance(
            quad_angles_raw, torso_angles_raw, phases.get("reps", []), fps
        )
        if glute_dominance and glute_dominance.get("status") != "error":
            result["glute_dominance"] = glute_dominance
        
        # Knee valgus only for front view
        if (_is_front_view(camera_angle_info) and 
            landmarks_list and 
            phases.get("reps")):
            knee_valgus = analyze_knee_valgus(landmarks_list, phases.get("reps", []))
            if knee_valgus and knee_valgus.get("status") != "error":
                result["knee_valgus"] = knee_valgus
        
        # Calculate final score
        result["final_score"] = calculate_final_score(result)
        
        return result
    
    def get_camera_angle_detector(self) -> Optional[Callable]:
        """Return camera angle detection function for squat."""
        return detect_camera_angle
    
    def _extract_active_angles(self, angles: List, phases: Dict) -> List:
        """Extract angles only from active squat phases."""
        if not phases.get("reps"):
            return angles
        
        active_angles = []
        for rep in phases["reps"]:
            active_angles.extend([
                angles[i] if i < len(angles) else None
                for i in range(rep["start_frame"], rep["end_frame"] + 1)
            ])
        return active_angles

