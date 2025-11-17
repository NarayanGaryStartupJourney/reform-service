# Livestream Compatibility Analysis for Calculation Functions

## Current Implementation

### Function Structure
All calculation functions currently expect:
- **Input**: `landmarks_list: list` - A list of MediaPipe pose landmarks from multiple frames
- **Processing**: Iterates through all frames to calculate averages or per-frame values
- **Output**: Either average values (float) or per-frame lists

### Current Functions

1. **Average Calculation Functions** (process entire video):
   - `calculate_torso_angle(landmarks_list)` → Returns average float
   - `calculate_quad_angle(landmarks_list)` → Returns average float
   - `calculate_ankle_angle(landmarks_list)` → Returns average float

2. **Per-Frame Calculation Functions** (process entire video):
   - `calculate_torso_angle_per_frame(landmarks_list)` → Returns list of angles
   - `calculate_quad_angle_per_frame(landmarks_list)` → Returns list of angles
   - `calculate_ankle_angle_per_frame(landmarks_list)` → Returns list of angles

3. **Core Helper Functions** (already frame-agnostic):
   - `get_segment_angle(point1, point2)` → Works on single points ✓
   - `get_ankle_segment_angle(point1, point2)` → Works on single points ✓

## Livestream Requirements

### Expected Behavior
- **Input**: Single frame's landmarks (or small batch)
- **Processing**: Real-time calculation for immediate feedback
- **Output**: Single angle value(s) for current frame
- **Frequency**: Process each frame as it arrives (e.g., 30 FPS)

## Compatibility Analysis

### ✅ COMPATIBLE (No Changes Needed)

**Helper Functions:**
- `get_segment_angle(point1, point2)` - Already works on single points
- `get_ankle_segment_angle(point1, point2)` - Already works on single points

These can be used directly with a single frame's landmarks.

### ⚠️ PARTIALLY COMPATIBLE (Minor Changes Needed)

**Per-Frame Functions:**
- `calculate_torso_angle_per_frame(landmarks_list)`
- `calculate_quad_angle_per_frame(landmarks_list)`
- `calculate_ankle_angle_per_frame(landmarks_list)`

**Issue**: These functions expect a list but can work with a single-item list `[landmarks]`.

**Solution**: Can be used as-is by passing `[single_frame_landmarks]`, but this is inefficient.

### ❌ NOT COMPATIBLE (New Functions Needed)

**Average Calculation Functions:**
- `calculate_torso_angle(landmarks_list)` - Calculates average across all frames
- `calculate_quad_angle(landmarks_list)` - Calculates average across all frames
- `calculate_ankle_angle(landmarks_list)` - Calculates average across all frames

**Issue**: These calculate averages across multiple frames, which doesn't make sense for livestream where we need real-time per-frame values.

**Solution**: For livestream, we should use the per-frame functions with a single frame, or create dedicated single-frame functions.

## Recommended Approach

### Option 1: Use Per-Frame Functions (Current)
```python
# For livestream - process single frame
landmarks = process_single_frame_with_pose(frame)  # Returns single landmarks object
landmarks_list = [landmarks]  # Wrap in list

torso_angle = calculate_torso_angle_per_frame(landmarks_list)[0]
quad_angle = calculate_quad_angle_per_frame(landmarks_list)[0]
ankle_angle = calculate_ankle_angle_per_frame(landmarks_list)[0]
```

**Pros**: Uses existing functions
**Cons**: Inefficient (creates list, processes list, extracts single value)

### Option 2: Create Single-Frame Functions (Recommended)
```python
def calculate_torso_angle_single(landmarks) -> float:
    """Calculates torso angle for a single frame."""
    if not landmarks:
        return None
    left_angle = get_segment_angle(landmarks.landmark[23], landmarks.landmark[11])
    right_angle = get_segment_angle(landmarks.landmark[24], landmarks.landmark[12])
    if left_angle is not None and right_angle is not None:
        return (left_angle + right_angle) / 2
    return None

def calculate_quad_angle_single(landmarks) -> float:
    """Calculates quad angle for a single frame."""
    # Similar implementation

def calculate_ankle_angle_single(landmarks) -> float:
    """Calculates ankle angle for a single frame."""
    # Similar implementation
```

**Pros**: 
- More efficient (no list overhead)
- Clearer intent for livestream use
- Better performance for real-time processing

**Cons**: 
- Code duplication (though minimal)
- Need to maintain both versions

### Option 3: Refactor to Support Both (Best Long-term)
Refactor existing functions to accept either:
- Single landmarks object
- List of landmarks

```python
def calculate_torso_angle(landmarks_or_list) -> float | list:
    """Calculates torso angle. Accepts single landmarks or list."""
    if isinstance(landmarks_or_list, list):
        # Process list (existing logic)
    else:
        # Process single frame
```

**Pros**: Single function for both use cases
**Cons**: More complex, type checking overhead

## Summary

### Current State
- **Helper functions**: ✅ Fully compatible
- **Per-frame functions**: ⚠️ Work but inefficient for single frames
- **Average functions**: ❌ Not suitable for livestream

### Recommendation
**For immediate livestream support**: Use Option 1 (wrap single frame in list)
**For optimal performance**: Implement Option 2 (single-frame functions)
**For long-term maintainability**: Consider Option 3 (unified functions)

### Implementation Priority
1. **Short-term**: Use existing per-frame functions with `[landmarks]` wrapper
2. **Medium-term**: Add single-frame helper functions for better performance
3. **Long-term**: Refactor to unified functions if codebase grows

## Code Changes Needed

### Minimal Changes (Option 1)
None - can use existing functions as-is

### Recommended Changes (Option 2)
Add three new functions:
- `calculate_torso_angle_single(landmarks) -> float`
- `calculate_quad_angle_single(landmarks) -> float`
- `calculate_ankle_angle_single(landmarks) -> float`

Each function should be < 20 lines and follow the same pattern as the per-frame versions but for a single frame.

