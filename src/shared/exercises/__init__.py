"""Exercise module registry and base interfaces."""

from .base import ExerciseBase
from .registry import get_exercise, EXERCISES

__all__ = ['ExerciseBase', 'get_exercise', 'EXERCISES']

