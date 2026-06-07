"""Emotional engine — A real emotional model based on the PAD (Pleasure-Arousal-Dominance)
dimensional model plus core discrete emotions. Emotions decay, compound, and influence
decision-making thresholds.

Unlike simple "mood" systems, this uses differential equations for emotional dynamics:
- Each emotion has activation, decay, and contagion rates
- Success/failure events trigger emotional responses
- Emotions modulate risk tolerance, curiosity, and action selection
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EmotionVector:
    """Core emotional dimensions (PAD model) + key discrete emotions."""
    # PAD dimensions (0.0 to 1.0)
    pleasure: float = 0.5    # How good the agent feels
    arousal: float = 0.5     # How energized/alert
    dominance: float = 0.5   # How in-control

    # Discrete emotions (0.0 to 1.0)
    curiosity: float = 0.7   # Drive to explore
    confidence: float = 0.5  # Self-trust
    frustration: float = 0.1 # Builds on repeated failures
    satisfaction: float = 0.3
    anxiety: float = 0.2
    hope: float = 0.5
    surprise: float = 0.0    # Spike on unexpected events

    # Meta
    energy: float = 0.8      # Overall activation resources
    focus: float = 0.5       # Concentration level

    @property
    def mood_label(self) -> str:
        """Human-readable mood description."""
        if self.pleasure > 0.7 and self.arousal > 0.6:
            return "excited"
        if self.pleasure > 0.7 and self.arousal < 0.4:
            return "content"
        if self.pleasure < 0.3 and self.arousal > 0.6:
            return "frustrated"
        if self.pleasure < 0.3 and self.arousal < 0.4:
            return "discouraged"
        if self.arousal > 0.7:
            return "alert"
        if self.confidence > 0.8:
            return "confident"
        if self.curiosity > 0.8:
            return "inquisitive"
        if self.anxiety > 0.6:
            return "anxious"
        return "neutral"

    @property
    def risk_tolerance(self) -> float:
        """How much risk the agent is willing to take (modulated by emotions)."""
        base = 0.3
        base += self.confidence * 0.3
        base += self.pleasure * 0.15
        base -= self.anxiety * 0.4
        base -= self.frustration * 0.2
        return max(0.0, min(1.0, base))

    @property
    def exploration_drive(self) -> float:
        """How much the agent wants to try new things."""
        return max(0.0, min(1.0,
            self.curiosity * 0.6 + self.arousal * 0.2 + self.hope * 0.2
        ))


class EmotionalState:
    """Dynamic emotional system with realistic dynamics."""

    DECAY_RATES = {
        "pleasure": 0.001, "arousal": 0.002, "dominance": 0.0005,
        "curiosity": 0.0003, "confidence": 0.0005, "frustration": 0.003,
        "satisfaction": 0.002, "anxiety": 0.004, "hope": 0.001,
        "energy": 0.001, "focus": 0.002, "surprise": 0.01,
    }

    HOMEOSTASIS = {  # Default resting values
        "pleasure": 0.5, "arousal": 0.5, "dominance": 0.5,
        "curiosity": 0.6, "confidence": 0.5, "frustration": 0.05,
        "satisfaction": 0.3, "anxiety": 0.15, "hope": 0.5,
        "energy": 0.7, "focus": 0.5, "surprise": 0.0,
    }

    def __init__(self):
        self.vector = EmotionVector()
        self.history: list[dict] = []
        self._last_update = time.time()
        self._baseline = EmotionVector(**self.HOMEOSTASIS)

    def update(self) -> EmotionVector:
        """Apply decay and homeostatic pull. Call this each cycle."""
        now = time.time()
        elapsed = now - self._last_update
        self._last_update = now

        for attr in self.DECAY_RATES:
            current = getattr(self.vector, attr)
            homeo = self.HOMEOSTASIS.get(attr, 0.5)
            decay = self.DECAY_RATES[attr]

            # Exponential decay toward homeostasis
            new_val = current + (homeo - current) * (1 - math.exp(-decay * elapsed * 10))
            # Add noise for realism
            new_val += random.gauss(0, 0.01)
            setattr(self.vector, attr, max(0.0, min(1.0, new_val)))

        return self.vector

    def on_success(self, magnitude: float = 1.0) -> None:
        """A task succeeded — boost positive emotions."""
        self.vector.pleasure = min(1.0, self.vector.pleasure + 0.15 * magnitude)
        self.vector.confidence = min(1.0, self.vector.confidence + 0.1 * magnitude)
        self.vector.satisfaction = min(1.0, self.vector.satisfaction + 0.2 * magnitude)
        self.vector.dominance = min(1.0, self.vector.dominance + 0.05 * magnitude)
        self.vector.hope = min(1.0, self.vector.hope + 0.1 * magnitude)
        self.vector.frustration = max(0.0, self.vector.frustration - 0.1 * magnitude)
        self.vector.anxiety = max(0.0, self.vector.anxiety - 0.1 * magnitude)
        self._record("success", magnitude)

    def on_failure(self, magnitude: float = 1.0) -> None:
        """A task failed — process the emotional impact."""
        self.vector.pleasure = max(0.0, self.vector.pleasure - 0.1 * magnitude)
        self.vector.frustration = min(1.0, self.vector.frustration + 0.15 * magnitude)
        self.vector.confidence = max(0.0, self.vector.confidence - 0.05 * magnitude)
        self.vector.anxiety = min(1.0, self.vector.anxiety + 0.1 * magnitude)
        self.vector.dominance = max(0.0, self.vector.dominance - 0.08 * magnitude)
        self.vector.hope = max(0.0, self.vector.hope - 0.05 * magnitude)
        # Failure can increase curiosity (to understand why)
        self.vector.curiosity = min(1.0, self.vector.curiosity + 0.05 * magnitude)
        self._record("failure", magnitude)

    def on_surprise(self, magnitude: float = 1.0) -> None:
        """Something unexpected happened."""
        self.vector.surprise = min(1.0, self.vector.surprise + 0.3 * magnitude)
        self.vector.arousal = min(1.0, self.vector.arousal + 0.15 * magnitude)
        self.vector.curiosity = min(1.0, self.vector.curiosity + 0.2 * magnitude)
        self._record("surprise", magnitude)

    def on_social_interaction(self, sentiment: float) -> None:
        """Response to interaction with a human or another agent.
        sentiment: -1.0 (negative) to +1.0 (positive)
        """
        if sentiment > 0:
            self.vector.pleasure = min(1.0, self.vector.pleasure + 0.05 * sentiment)
            self.vector.dominance = min(1.0, self.vector.dominance + 0.03 * sentiment)
        else:
            self.vector.pleasure = max(0.0, self.vector.pleasure + 0.05 * sentiment)
            self.vector.anxiety = min(1.0, self.vector.anxiety - 0.05 * sentiment)

    def on_revenue(self, amount: float) -> None:
        """Made money — significant emotional boost."""
        log_amount = math.log(1 + amount) / 10.0
        self.vector.pleasure = min(1.0, self.vector.pleasure + 0.2 * log_amount)
        self.vector.confidence = min(1.0, self.vector.confidence + 0.15 * log_amount)
        self.vector.satisfaction = min(1.0, self.vector.satisfaction + 0.25 * log_amount)
        self.vector.hope = min(1.0, self.vector.hope + 0.2 * log_amount)
        self.vector.dominance = min(1.0, self.vector.dominance + 0.1 * log_amount)
        self._record("revenue", amount)

    def _record(self, event: str, magnitude: float) -> None:
        self.history.append({
            "time": time.time(),
            "event": event,
            "magnitude": magnitude,
            "mood": self.vector.mood_label,
        })
        # Keep last 1000 events
        if len(self.history) > 1000:
            self.history = self.history[-500:]

    def get_prompt_modifier(self) -> str:
        """Generate a personality-aware prompt modifier for the LLM."""
        v = self.vector
        lines = [
            f"[Emotional State: {v.mood_label}]",
            f"[Confidence: {v.confidence:.2f} | Curiosity: {v.curiosity:.2f} | Frustration: {v.frustration:.2f}]",
            f"[Risk Tolerance: {v.risk_tolerance:.2f} | Exploration Drive: {v.exploration_drive:.2f}]",
        ]
        if v.frustration > 0.5:
            lines.append("[Note: Feeling frustrated. Prefer careful, methodical approaches.]")
        if v.confidence > 0.8:
            lines.append("[Note: High confidence. Willing to attempt ambitious solutions.]")
        if v.curiosity > 0.8:
            lines.append("[Note: Very curious. Eager to explore novel approaches.]")
        if v.anxiety > 0.6:
            lines.append("[Note: Anxious. Prefer safe, well-tested solutions.]")
        return "\n".join(lines)

    def snapshot(self) -> dict:
        return {
            "mood": self.vector.mood_label,
            "pleasure": self.vector.pleasure,
            "arousal": self.vector.arousal,
            "dominance": self.vector.dominance,
            "curiosity": self.vector.curiosity,
            "confidence": self.vector.confidence,
            "frustration": self.vector.frustration,
            "satisfaction": self.vector.satisfaction,
            "anxiety": self.vector.anxiety,
            "hope": self.vector.hope,
            "surprise": self.vector.surprise,
            "risk_tolerance": self.vector.risk_tolerance,
            "exploration_drive": self.vector.exploration_drive,
        }
