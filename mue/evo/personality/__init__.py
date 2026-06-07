"""Personality Engine — Emotional state vector that evolves with experience.

The agent has genuine emotional dynamics: emotions influence decisions,
decisions produce outcomes, outcomes reshape emotions. This creates a
real feedback loop that generates authentic personality over time.
"""

from .emotions import EmotionalState, EmotionVector
from .persona import Persona, Trait

__all__ = ["EmotionalState", "EmotionVector", "Persona", "Trait"]
