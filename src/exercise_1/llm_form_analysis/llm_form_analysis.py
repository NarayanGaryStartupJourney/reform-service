"""Exercise 1 form analysis component."""


def _is_local_max(i: int, angles_with_indices: list, min_height: float) -> bool:
    """Checks if index i is a local maximum above min_height."""
    if i < 2 or i >= len(angles_with_indices) - 2:
        return False
    prev2, prev1 = angles_with_indices[i-2][1], angles_with_indices[i-1][1]
    curr = angles_with_indices[i][1]
    next1, next2 = angles_with_indices[i+1][1], angles_with_indices[i+2][1]
    return curr > prev1 and curr > next1 and curr >= min_height and curr > prev2 and curr > next2


def _filter_peaks_by_distance(candidates: list, min_distance: int) -> list:
    """Filters candidate peaks by minimum distance between them."""
    if not candidates:
        return []
    peaks = [candidates[0]]
    for idx, peak_data in candidates[1:]:
        frame_diff = idx - peaks[-1][0]
        if frame_diff >= min_distance:
            peaks.append((idx, peak_data))
        elif peak_data[1] > peaks[-1][1][1]:
            peaks[-1] = (idx, peak_data)
    return [p[1] for p in peaks]


def _find_peaks(angles_with_indices: list, min_height: float, min_distance: int = 30) -> list:
    """Finds local maxima (peaks) representing bottom of squat."""
    candidates = [(i, angles_with_indices[i]) for i in range(2, len(angles_with_indices) - 2)
                  if _is_local_max(i, angles_with_indices, min_height)]
    return _filter_peaks_by_distance(candidates, min_distance)


def _filter_bounce_reps(peaks_with_indices: list, angles_with_indices: list, bounce_threshold: int = 60) -> list:
    """Filters out bounce patterns (two close peaks = one rep)."""
    if len(peaks_with_indices) < 2:
        return peaks_with_indices
    filtered = [peaks_with_indices[0]]
    for i in range(1, len(peaks_with_indices)):
        prev_idx, prev_peak_data = peaks_with_indices[i-1]
        curr_idx, curr_peak_data = peaks_with_indices[i]
        if curr_idx - prev_idx < bounce_threshold and curr_peak_data[1] >= prev_peak_data[1] * 0.9:
            filtered[-1] = (curr_idx, curr_peak_data)
        else:
            filtered.append((curr_idx, curr_peak_data))
    return filtered


def _find_rep_start_end(angles_with_indices: list, peak_frame: int, baseline: float, threshold: float) -> tuple:
    """Finds start and end frames for a single rep around a peak."""
    peak_idx = next(i for i, (f, _) in enumerate(angles_with_indices) if f == peak_frame)
    start_frame = None
    for i in range(peak_idx - 1, -1, -1):
        if angles_with_indices[i][1] < threshold:
            start_frame = angles_with_indices[i+1][0] if i+1 <= peak_idx else peak_frame
            break
    if start_frame is None:
        start_frame = angles_with_indices[0][0]
    end_frame = None
    for i in range(peak_idx + 1, len(angles_with_indices)):
        if angles_with_indices[i][1] < threshold:
            end_frame = angles_with_indices[i-1][0] if i-1 >= peak_idx else peak_frame
            break
    if end_frame is None:
        end_frame = angles_with_indices[-1][0]
    return start_frame, end_frame


def _calculate_baseline(valid_angles: list) -> float:
    """Calculates baseline angle from first/last frames."""
    if len(valid_angles) > 20:
        return min([a for _, a in valid_angles[:10]] + [a for _, a in valid_angles[-10:]])
    return min([a for _, a in valid_angles])


def _build_reps_from_peaks(filtered_peaks: list, valid_angles: list, baseline: float, threshold: float) -> list:
    """Builds rep list from filtered peaks."""
    reps = []
    for peak_idx, (peak_frame, peak_angle) in filtered_peaks:
        start_frame, end_frame = _find_rep_start_end(valid_angles, peak_frame, baseline, threshold)
        if start_frame is not None and end_frame is not None and start_frame < end_frame:
            reps.append({"start_frame": start_frame, "bottom_frame": peak_frame, "end_frame": end_frame})
    return reps


def detect_squat_phases(quad_angles_per_frame: list, fps: float = 30.0) -> dict:
    """Detects all squat reps. Filters bounce patterns."""
    if not quad_angles_per_frame or all(a is None for a in quad_angles_per_frame):
        return {"reps": []}
    valid_angles = [(i, a) for i, a in enumerate(quad_angles_per_frame) if a is not None]
    if not valid_angles:
        return {"reps": []}
    baseline = _calculate_baseline(valid_angles)
    squat_threshold = baseline + 20
    peaks = _find_peaks(valid_angles, squat_threshold)
    if not peaks:
        return {"reps": []}
    bounce_threshold_frames = int(fps * 1.0)
    peaks_with_indices = [(next(i for i, (f, _) in enumerate(valid_angles) if f == p[0]), p) for p in peaks]
    filtered_peaks = _filter_bounce_reps(peaks_with_indices, valid_angles, bounce_threshold_frames)
    return {"reps": _build_reps_from_peaks(filtered_peaks, valid_angles, baseline, squat_threshold)}


def _filter_to_active_phases(torso_angles_per_frame: list, quad_angles_per_frame: list) -> list:
    """Filters torso angles to only active squat phases."""
    phases = detect_squat_phases(quad_angles_per_frame)
    if not phases.get("reps"):
        return torso_angles_per_frame
    active_frames = []
    for rep in phases["reps"]:
        active_frames.extend(range(rep["start_frame"], rep["end_frame"] + 1))
    if not active_frames:
        return torso_angles_per_frame
    return [torso_angles_per_frame[i] if i < len(torso_angles_per_frame) else None for i in active_frames]


def _calculate_torso_metrics(valid_angles: list) -> tuple:
    """Calculates max, avg, and range from valid angles."""
    max_angle = max(valid_angles)
    avg_angle = sum(valid_angles) / len(valid_angles)
    angle_range = max(valid_angles) - min(valid_angles)
    return max_angle, avg_angle, angle_range


def _determine_torso_status(max_angle: float, avg_angle: float) -> tuple:
    """Determines status, score, and message based on torso angle metrics."""
    if max_angle <= 43:
        if 35 <= avg_angle <= 43:
            return "good", 100, f"Excellent torso position. Average forward lean: {avg_angle:.1f}° (within research-based optimal range: 35-43°)."
        elif avg_angle < 35:
            return "good", 95, f"Good torso position. Average forward lean: {avg_angle:.1f}° (below optimal 35-43° range, but acceptable)."
        else:
            return "good", 90, f"Good torso position. Average forward lean: {avg_angle:.1f}° (within acceptable range, optimal: 35-43°)."
    elif max_angle <= 45:
        return "warning", 75, f"Moderate forward lean detected. Max angle: {max_angle:.1f}° (slightly above optimal 35-43° range). Maintain upright posture to optimize performance."
    else:
        return "poor", 50, f"Excessive forward lean detected. Max angle: {max_angle:.1f}° (>45°). Research indicates this exceeds recommended range and may reduce squat effectiveness."


def analyze_torso_angle(torso_angles_per_frame: list, quad_angles_per_frame: list = None, validation_result: dict = None) -> dict:
    """Analyzes torso angle for squat form using evidence-based thresholds."""
    if not torso_angles_per_frame or all(a is None for a in torso_angles_per_frame):
        if validation_result and validation_result.get("valid_frame_percentage", 1.0) < 0.3:
            return {"status": "error", "message": f"Insufficient pose detection ({validation_result.get('valid_frame_percentage', 0):.0%} of frames). Please ensure person is fully visible."}
        return {"status": "error", "message": "No torso angle data available"}
    if quad_angles_per_frame:
        torso_angles_per_frame = _filter_to_active_phases(torso_angles_per_frame, quad_angles_per_frame)
    valid_angles = [a for a in torso_angles_per_frame if a is not None]
    if not valid_angles:
        return {"status": "error", "message": "No valid torso angle data"}
    max_angle, avg_angle, angle_range = _calculate_torso_metrics(valid_angles)
    status, score, message = _determine_torso_status(max_angle, avg_angle)
    return {"status": status, "score": score, "message": message, "max_angle": round(max_angle, 1),
            "avg_angle": round(avg_angle, 1), "angle_range": round(angle_range, 1)}


def _calculate_quad_metrics(valid_angles: list) -> tuple:
    """Calculates max (max depth), avg, and range from valid quad angles."""
    max_angle = max(valid_angles)
    avg_angle = sum(valid_angles) / len(valid_angles)
    angle_range = max(valid_angles) - min(valid_angles)
    return max_angle, avg_angle, angle_range


def _determine_quad_status(max_angle: float, avg_angle: float) -> tuple:
    """Determines status, score, and message based on quad angle (depth) metrics."""
    if max_angle >= 70:
        return "good", 100, f"Excellent squat depth. Maximum quad angle: {max_angle:.1f}° (full depth achieved, hip crease below knee)."
    elif max_angle >= 60:
        return "warning", 75, f"Partial squat depth. Maximum quad angle: {max_angle:.1f}° (hip crease at or slightly above knee). Aim for deeper squats (quad angle ≥70°) for optimal muscle activation."
    else:
        return "poor", 50, f"Insufficient squat depth. Maximum quad angle: {max_angle:.1f}° (<60°). Research indicates full depth (hip crease below knee, quad angle ≥70°) is important for muscle development and safety."


def analyze_quad_angle(quad_angles_per_frame: list) -> dict:
    """Analyzes quad angle (squat depth) using evidence-based thresholds."""
    if not quad_angles_per_frame or all(a is None for a in quad_angles_per_frame):
        return {"status": "error", "message": "No quad angle data available"}
    valid_angles = [a for a in quad_angles_per_frame if a is not None]
    if not valid_angles:
        return {"status": "error", "message": "No valid quad angle data"}
    max_angle, avg_angle, angle_range = _calculate_quad_metrics(valid_angles)
    status, score, message = _determine_quad_status(max_angle, avg_angle)
    return {"status": status, "score": score, "message": message, "max_angle": round(max_angle, 1),
            "avg_angle": round(avg_angle, 1), "angle_range": round(angle_range, 1)}


def _calculate_ankle_metrics(valid_angles: list) -> tuple:
    """Calculates min (max dorsiflexion), avg, and range from valid ankle angles."""
    min_angle = min(valid_angles)
    avg_angle = sum(valid_angles) / len(valid_angles)
    angle_range = max(valid_angles) - min(valid_angles)
    return min_angle, avg_angle, angle_range


def _determine_ankle_status(min_angle: float, avg_angle: float) -> tuple:
    """Determines status, score, and message based on ankle angle (mobility) metrics."""
    if min_angle <= 60:
        return "good", 100, f"Good ankle mobility. Minimum angle: {min_angle:.1f}° (adequate dorsiflexion range observed)."
    elif min_angle <= 70:
        return "warning", 75, f"Moderate ankle mobility. Minimum angle: {min_angle:.1f}° (may limit squat depth). Research indicates limited ankle dorsiflexion can restrict squat depth."
    else:
        return "poor", 50, f"Limited ankle mobility. Minimum angle: {min_angle:.1f}° (>70°). Research shows restricted dorsiflexion can limit squat depth and cause compensation patterns."


def analyze_ankle_angle(ankle_angles_per_frame: list) -> dict:
    """Analyzes ankle angle (ankle mobility/dorsiflexion). Research shows limited dorsiflexion restricts squat depth."""
    if not ankle_angles_per_frame or all(a is None for a in ankle_angles_per_frame):
        return {"status": "error", "message": "No ankle angle data available"}
    valid_angles = [a for a in ankle_angles_per_frame if a is not None]
    if not valid_angles:
        return {"status": "error", "message": "No valid ankle angle data"}
    min_angle, avg_angle, angle_range = _calculate_ankle_metrics(valid_angles)
    status, score, message = _determine_ankle_status(min_angle, avg_angle)
    return {"status": status, "score": score, "message": message, "min_angle": round(min_angle, 1),
            "avg_angle": round(avg_angle, 1), "angle_range": round(angle_range, 1)}


def _calculate_asymmetry_metrics(valid_asymmetry: list) -> tuple:
    """Calculates max absolute, avg, and range from valid asymmetry values."""
    abs_asymmetry = [abs(a) for a in valid_asymmetry]
    max_asymmetry = max(abs_asymmetry)
    avg_asymmetry = sum(valid_asymmetry) / len(valid_asymmetry)
    avg_abs_asymmetry = sum(abs_asymmetry) / len(abs_asymmetry)
    return max_asymmetry, avg_asymmetry, avg_abs_asymmetry


def _determine_asymmetry_status(max_asymmetry: float, avg_abs_asymmetry: float, side: str) -> tuple:
    """Determines status, score, and message based on asymmetry metrics."""
    if max_asymmetry < 5:
        return "good", 100, f"Minimal asymmetry detected. Maximum difference: {max_asymmetry:.1f}° (within acceptable range <5°)."
    elif max_asymmetry < 10:
        return "warning", 75, f"Moderate {side} asymmetry detected. Maximum difference: {max_asymmetry:.1f}° (5-10° range). Research indicates asymmetries >10% may require compensatory strategies."
    else:
        return "poor", 50, f"Significant {side} asymmetry detected. Maximum difference: {max_asymmetry:.1f}° (>10°). Research shows asymmetries >10° can increase injury risk and impair performance."


def analyze_asymmetry(asymmetry_per_frame: list, asymmetry_type: str) -> dict:
    """Analyzes asymmetry using research-based thresholds (<5° good, 5-10° warning, >10° poor)."""
    if not asymmetry_per_frame or all(a is None for a in asymmetry_per_frame):
        return {"status": "error", "message": f"No {asymmetry_type} asymmetry data available"}
    valid_asymmetry = [a for a in asymmetry_per_frame if a is not None]
    if not valid_asymmetry:
        return {"status": "error", "message": f"No valid {asymmetry_type} asymmetry data"}
    max_asymmetry, avg_asymmetry, avg_abs_asymmetry = _calculate_asymmetry_metrics(valid_asymmetry)
    status, score, message = _determine_asymmetry_status(max_asymmetry, avg_abs_asymmetry, asymmetry_type)
    return {"status": status, "score": score, "message": message, "max_asymmetry": round(max_asymmetry, 1),
            "avg_asymmetry": round(avg_asymmetry, 1), "avg_abs_asymmetry": round(avg_abs_asymmetry, 1)}


def _extract_per_rep_metrics(angles_per_frame: list, reps: list, metric_type: str) -> list:
    """Extracts per-rep metrics (max for depth, avg for torso/asymmetry)."""
    per_rep_values = []
    for rep in reps:
        rep_frames = range(rep["start_frame"], rep["end_frame"] + 1)
        rep_angles = [angles_per_frame[i] if i < len(angles_per_frame) and angles_per_frame[i] is not None
                     else None for i in rep_frames]
        valid_angles = [a for a in rep_angles if a is not None]
        if not valid_angles:
            continue
        if metric_type == "max":
            per_rep_values.append(max(valid_angles))
        else:
            per_rep_values.append(sum(valid_angles) / len(valid_angles))
    return per_rep_values


def _calculate_consistency_metrics(per_rep_values: list) -> tuple:
    """Calculates mean, std dev, and coefficient of variation."""
    if len(per_rep_values) < 2:
        return None, None, None
    mean_val = sum(per_rep_values) / len(per_rep_values)
    variance = sum((x - mean_val) ** 2 for x in per_rep_values) / len(per_rep_values)
    std_dev = variance ** 0.5
    cv = (std_dev / mean_val * 100) if mean_val != 0 else None
    return mean_val, std_dev, cv


def _determine_consistency_status(cv: float, metric_name: str) -> tuple:
    """Determines status based on coefficient of variation."""
    if cv is None:
        return "error", 0, "Insufficient data for consistency analysis"
    if cv < 5:
        return "good", 100, f"Excellent {metric_name} consistency (CV: {cv:.1f}%). Reps are very consistent."
    elif cv < 10:
        return "warning", 75, f"Moderate {metric_name} variability (CV: {cv:.1f}%). Some inconsistency detected across reps."
    else:
        return "poor", 50, f"Significant {metric_name} variability (CV: {cv:.1f}%). High inconsistency suggests fatigue or form breakdown."


def _build_consistency_result(status: str, cv: float, mean: float, std: float, message: str) -> dict:
    """Builds consistency result dict."""
    return {"status": status, "cv": round(cv, 1) if cv else None,
            "mean": round(mean, 1) if mean else None, "std": round(std, 1) if std else None, "message": message}


def _analyze_single_consistency(values: list, metric_name: str) -> tuple:
    """Analyzes consistency for a single metric and returns status, score, and result dict."""
    mean_val, std_val, cv = _calculate_consistency_metrics(values)
    status, score, message = _determine_consistency_status(cv, metric_name) if cv else ("error", 0, f"No {metric_name} data")
    return status, score, _build_consistency_result(status, cv, mean_val, std_val, message)


def analyze_rep_consistency(angles_per_frame: list, asymmetry_per_frame: dict, reps: list) -> dict:
    """Analyzes rep-to-rep consistency for depth, torso, and asymmetry."""
    if not reps or len(reps) < 2:
        return {"status": "error", "message": "Need at least 2 reps for consistency analysis"}
    depth_values = _extract_per_rep_metrics(angles_per_frame.get("quad_angle", []), reps, "max")
    torso_values = _extract_per_rep_metrics(angles_per_frame.get("torso_angle", []), reps, "avg")
    quad_asymmetry_values = _extract_per_rep_metrics(asymmetry_per_frame.get("quad_asymmetry", []), reps, "avg")
    depth_status, depth_score, depth_result = _analyze_single_consistency(depth_values, "depth")
    torso_status, torso_score, torso_result = _analyze_single_consistency(torso_values, "torso")
    asym_status, asym_score, asym_result = _analyze_single_consistency(quad_asymmetry_values, "asymmetry")
    overall_score = int((depth_score + torso_score + asym_score) / 3) if all([depth_score, torso_score, asym_score]) else 0
    overall_status = "good" if all(s in ["good", "warning"] for s in [depth_status, torso_status, asym_status]) else "warning" if any(s == "poor" for s in [depth_status, torso_status, asym_status]) else "poor"
    return {"status": overall_status, "score": overall_score, "rep_count": len(reps),
            "depth_consistency": depth_result, "torso_consistency": torso_result, "asymmetry_consistency": asym_result}


def _determine_grade(final_score: int) -> str:
    """Determines grade based on final score."""
    if final_score >= 90:
        return "Excellent"
    elif final_score >= 75:
        return "Good"
    elif final_score >= 60:
        return "Fair"
    else:
        return "Needs Improvement"


def _calculate_smoothed_baseline(angles: list, start_frame: int, window: int = 3) -> float:
    """Calculates smoothed baseline from first few frames."""
    valid = [angles[i] for i in range(start_frame, min(start_frame + window, len(angles)))
             if i < len(angles) and angles[i] is not None]
    return sum(valid) / len(valid) if valid else (angles[start_frame] if start_frame < len(angles) and angles[start_frame] is not None else 0)


def _detect_movement_start_velocity(angles: list, start_frame: int, end_frame: int, fps: float) -> int:
    """Detects movement start using velocity (rate of change). Returns frame index."""
    if start_frame >= len(angles) or end_frame >= len(angles) or end_frame <= start_frame:
        return start_frame
    baseline = _calculate_smoothed_baseline(angles, start_frame, 3)
    velocity_threshold = 2.0 / fps
    for i in range(start_frame + 1, min(end_frame + 1, len(angles))):
        if angles[i] is not None and angles[i-1] is not None:
            velocity = abs(angles[i] - angles[i-1]) * fps
            if velocity >= velocity_threshold and abs(angles[i] - baseline) >= 3.0:
                return i
    return start_frame


def _calculate_glute_dominance_metrics(quad_angles: list, torso_angles: list, reps: list, fps: float) -> dict:
    """Calculates glute vs quad dominance metrics per rep during descent phase only."""
    if not reps or len(reps) < 1:
        return {"status": "error", "message": "No reps available for analysis"}
    timing_diffs_ms = []
    for rep in reps:
        start = rep["start_frame"]
        bottom = rep.get("bottom_frame", rep["end_frame"])
        hip_start = _detect_movement_start_velocity(torso_angles, start, bottom, fps)
        knee_start = _detect_movement_start_velocity(quad_angles, start, bottom, fps)
        timing_diff_frames = hip_start - knee_start
        timing_diff_ms = (timing_diff_frames / fps) * 1000
        timing_diffs_ms.append(timing_diff_ms)
    avg_timing_diff_ms = sum(timing_diffs_ms) / len(timing_diffs_ms) if timing_diffs_ms else 0
    return {"avg_timing_diff_ms": round(avg_timing_diff_ms, 1),
            "per_rep_diffs_ms": [round(d, 1) for d in timing_diffs_ms]}


def _determine_glute_dominance_status(avg_timing_diff_ms: float) -> tuple:
    """Determines status based on hip-knee timing. Positive = hip before knee (hip-dominant, preferred)."""
    if avg_timing_diff_ms >= 50:
        return "good", 100, f"Hip-dominant pattern detected. Hip movement initiates {avg_timing_diff_ms:.0f}ms before knee movement. Research indicates this reduces knee stress and enhances gluteal engagement."
    elif avg_timing_diff_ms >= -50:
        return "warning", 75, f"Mixed pattern detected. Hip and knee timing similar ({avg_timing_diff_ms:.0f}ms). Research suggests initiating with hips to improve glute engagement."
    else:
        return "poor", 50, f"Quad-dominant pattern detected. Knee initiates {abs(avg_timing_diff_ms):.0f}ms before hip. Research indicates this increases anterior knee stress and injury risk."


def analyze_glute_dominance(quad_angles_per_frame: list, torso_angles_per_frame: list, reps: list, fps: float = 30.0) -> dict:
    """Analyzes glute vs quad dominance based on hip-knee movement timing during descent phase."""
    if not quad_angles_per_frame or not torso_angles_per_frame:
        return {"status": "error", "message": "Missing angle data"}
    if not reps:
        return {"status": "error", "message": "No reps available"}
    metrics = _calculate_glute_dominance_metrics(quad_angles_per_frame, torso_angles_per_frame, reps, fps)
    if metrics.get("status") == "error":
        return metrics
    status, score, message = _determine_glute_dominance_status(metrics["avg_timing_diff_ms"])
    return {"status": status, "score": score, "message": message,
            "avg_timing_diff_ms": metrics["avg_timing_diff_ms"],
            "per_rep_diffs_ms": metrics["per_rep_diffs_ms"]}


def _is_front_view(camera_angle_info: dict) -> bool:
    """Checks if camera view is front (0deg) based on camera angle info."""
    if not camera_angle_info:
        return False
    angle_estimate = camera_angle_info.get("angle_estimate")
    if angle_estimate is None:
        return False
    return abs(angle_estimate - 0) <= 10


def _calculate_knee_valgus_angle(hip, knee, ankle) -> float:
    """Calculates FPPA: angle at knee joint (hip-knee-ankle). 180° = neutral, <180° = valgus, >180° = varus."""
    import math
    vec1_x, vec1_y = hip.x - knee.x, hip.y - knee.y
    vec2_x, vec2_y = ankle.x - knee.x, ankle.y - knee.y
    dot = vec1_x * vec2_x + vec1_y * vec2_y
    cross = vec1_x * vec2_y - vec1_y * vec2_x
    mag1 = math.sqrt(vec1_x**2 + vec1_y**2)
    mag2 = math.sqrt(vec2_x**2 + vec2_y**2)
    if mag1 == 0 or mag2 == 0:
        return None
    cos_angle = dot / (mag1 * mag2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    angle_rad = math.acos(cos_angle)
    if cross > 0:
        angle_rad = 2 * math.pi - angle_rad
    fppa = math.degrees(angle_rad)
    return fppa


def _calculate_valgus_per_frame(landmarks_list: list, reps: list) -> list:
    """Calculates knee valgus (FPPA) for each frame during active squat phases."""
    if not landmarks_list or not reps:
        return []
    valgus_angles = []
    active_frames = set()
    for rep in reps:
        active_frames.update(range(rep["start_frame"], rep["end_frame"] + 1))
    for i, landmarks in enumerate(landmarks_list):
        if i not in active_frames or not landmarks:
            valgus_angles.append(None)
            continue
        left_valgus = _calculate_knee_valgus_angle(landmarks.landmark[23], landmarks.landmark[25], landmarks.landmark[27])
        right_valgus = _calculate_knee_valgus_angle(landmarks.landmark[24], landmarks.landmark[26], landmarks.landmark[28])
        if left_valgus is not None and right_valgus is not None:
            avg_fppa = (left_valgus + right_valgus) / 2
            valgus_angles.append(avg_fppa)
        else:
            valgus_angles.append(None)
    return valgus_angles


def _calculate_valgus_metrics(valid_fppa: list) -> tuple:
    """Calculates max, avg, and range from FPPA angles. Also calculates max deviation from 180°."""
    max_fppa = max(valid_fppa)
    min_fppa = min(valid_fppa)
    avg_fppa = sum(valid_fppa) / len(valid_fppa)
    fppa_range = max_fppa - min_fppa
    deviations = [abs(180 - f) for f in valid_fppa]
    max_deviation_from_180 = max(deviations)
    most_extreme_idx = deviations.index(max_deviation_from_180)
    most_extreme_fppa = valid_fppa[most_extreme_idx]
    return max_fppa, avg_fppa, fppa_range, max_deviation_from_180, most_extreme_fppa


def _determine_valgus_status(max_fppa: float, avg_fppa: float, max_deviation: float, most_extreme_fppa: float) -> tuple:
    """Determines status based on FPPA deviation from 180°. <180° = valgus, >180° = varus."""
    if max_deviation < 4:
        return "good", 100, f"Minimal knee valgus/varus detected. FPPA: {most_extreme_fppa:.1f}° (deviation from 180°: {max_deviation:.1f}°). Research indicates this is within safe range."
    elif max_deviation < 8:
        valgus_varus = "valgus" if most_extreme_fppa < 180 else "varus"
        if most_extreme_fppa < 180:
            return "warning", 75, f"Moderate knee valgus detected. FPPA: {most_extreme_fppa:.1f}° (deviation: {max_deviation:.1f}°). Research suggests this may increase injury risk. Focus on hip abductor and external rotator strength."
        else:
            return "warning", 75, f"Moderate knee varus detected. FPPA: {most_extreme_fppa:.1f}° (deviation: {max_deviation:.1f}°). While less commonly associated with ACL injuries than valgus, varus alignment may indicate biomechanical issues. Consider addressing movement patterns."
    else:
        if most_extreme_fppa < 180:
            return "poor", 50, f"Significant knee valgus detected. FPPA: {most_extreme_fppa:.1f}° (knee inward, deviation: {max_deviation:.1f}°). Research indicates valgus significantly increases risk of ACL and patellofemoral injuries. Address hip abductor and external rotator weakness, and improve movement patterns."
        else:
            return "warning", 75, f"Significant knee varus detected. FPPA: {most_extreme_fppa:.1f}° (knee outward, deviation: {max_deviation:.1f}°). While varus is less commonly associated with ACL injuries than valgus, significant varus may indicate biomechanical issues or compensation patterns. Consider addressing movement patterns and lower limb alignment."


def analyze_knee_valgus(landmarks_list: list, reps: list) -> dict:
    """Analyzes knee valgus using FPPA. 180° = neutral, <180° = valgus, >180° = varus. Only valid for front view (0deg)."""
    if not landmarks_list or not reps:
        return {"status": "error", "message": "Missing landmarks or rep data"}
    fppa_angles = _calculate_valgus_per_frame(landmarks_list, reps)
    valid_fppa = [f for f in fppa_angles if f is not None]
    if not valid_fppa:
        return {"status": "error", "message": "No valid FPPA data available"}
    max_fppa, avg_fppa, fppa_range, max_deviation, most_extreme_fppa = _calculate_valgus_metrics(valid_fppa)
    status, score, message = _determine_valgus_status(max_fppa, avg_fppa, max_deviation, most_extreme_fppa)
    return {"status": status, "score": score, "message": message, "max_fppa": round(max_fppa, 1),
            "avg_fppa": round(avg_fppa, 1), "fppa_range": round(fppa_range, 1),
            "max_deviation_from_180": round(max_deviation, 1), "fppa_per_frame": fppa_angles}


def calculate_final_score(form_analysis: dict) -> dict:
    """Calculates weighted final score: Torso 25%, Quad 25%, Glute/Quad Dominance 12%, Rep Consistency 18%, Torso Asymmetry 8%, Quad Asymmetry 7%, Ankle Asymmetry 5%."""
    weights = {"torso_angle": 0.25, "quad_angle": 0.25, "glute_dominance": 0.12,
               "rep_consistency": 0.18, "torso_asymmetry": 0.08, "quad_asymmetry": 0.07, "ankle_asymmetry": 0.05}
    weighted_sum = 0.0
    total_weight = 0.0
    component_scores = {}
    for key, weight in weights.items():
        analysis = form_analysis.get(key)
        if analysis and analysis.get("score") is not None:
            score = analysis["score"]
            weighted_sum += score * weight
            total_weight += weight
            component_scores[key] = score
    final_score = int(weighted_sum / total_weight) if total_weight > 0 else 0
    return {"final_score": final_score, "grade": _determine_grade(final_score),
            "component_scores": component_scores, "weights": weights}

