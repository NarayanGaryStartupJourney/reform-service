"""
Exercise registry - central registry for all exercise implementations.

New exercises can be added by:
1. Creating exercise_N/ directory with implementation
2. Creating ExerciseN class inheriting from ExerciseBase
3. Registering it here
"""

from typing import Dict, Optional
from .base import ExerciseBase

# Registry will be populated by exercise modules
_EXERCISE_REGISTRY: Dict[int, ExerciseBase] = {}


def register_exercise(exercise: ExerciseBase) -> None:
    """Register an exercise implementation."""
    _EXERCISE_REGISTRY[exercise.exercise_id] = exercise


def get_exercise(exercise_id: int) -> Optional[ExerciseBase]:
    """
    Get exercise implementation by ID.
    
    Args:
        exercise_id: Exercise ID (1, 2, 3, etc.)
        
    Returns:
        ExerciseBase instance or None if not found
    """
    return _EXERCISE_REGISTRY.get(exercise_id)


def get_all_exercises() -> Dict[int, ExerciseBase]:
    """Get all registered exercises."""
    return _EXERCISE_REGISTRY.copy()


# Import and register exercises
# This will be populated when exercise modules are imported
def _register_exercises():
    """Register all exercise implementations."""
    # Import exercise modules to trigger registration
    try:
        from src.exercise_1.exercise import Exercise1
        register_exercise(Exercise1())
    except ImportError:
        pass  # Exercise 1 not yet refactored
    
    try:
        from src.exercise_2.exercise import Exercise2
        register_exercise(Exercise2())
    except ImportError:
        pass  # Exercise 2 not yet implemented
    
    try:
        from src.exercise_3.exercise import Exercise3
        register_exercise(Exercise3())
    except ImportError:
        pass  # Exercise 3 not yet implemented


# Auto-register on import
# Note: This runs when the module is imported
# Exercises will be registered when app.py imports from shared.exercises
try:
    _register_exercises()
except Exception:
    # Silently fail if exercises can't be registered yet
    # They'll be registered when modules are imported
    pass

# Public registry access
EXERCISES = _EXERCISE_REGISTRY

