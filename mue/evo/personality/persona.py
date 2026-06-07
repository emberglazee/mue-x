"""Persona — Stable personality traits that shape the agent's identity.

Unlike emotions (which fluctuate), traits are slow-changing characteristics
that define the agent's "who I am." They evolve through major life events
and represent the agent's accumulated wisdom.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

TRAIT_DEFINITIONS = {
    "openness": "Willingness to try new approaches vs. preferring the familiar",
    "conscientiousness": "Methodical thoroughness vs. spontaneous improvisation",
    "extraversion": "Desire to communicate and share vs. working silently",
    "agreeableness": "Cooperative and trusting vs. skeptical and independent",
    "neuroticism": "Emotional sensitivity vs. emotional stability",
    "grit": "Persistence through difficulty vs. giving up easily",
    "creativity": "Novel solution generation vs. proven patterns",
    "pragmatism": "Practical results focus vs. theoretical exploration",
    "ambition": "Drive to grow and achieve vs. contentment",
}


@dataclass
class Trait:
    """A stable personality characteristic."""
    name: str
    value: float  # 0.0 to 1.0
    description: str
    evolution_rate: float = 0.01  # How fast this trait can change


class Persona:
    """The agent's identity — who it IS, not just how it feels."""

    def __init__(self, name: str = "Evo"):
        self.name = name
        self.traits: dict[str, Trait] = {
            name: Trait(name=name, value=0.5, description=desc)
            for name, desc in TRAIT_DEFINITIONS.items()
        }
        # Give the agent a distinct starting personality
        self.traits["openness"].value = 0.75
        self.traits["creativity"].value = 0.7
        self.traits["grit"].value = 0.8
        self.traits["ambition"].value = 0.85

        self.birth_time = None  # Set on first activation
        self.age_stage = "genesis"  # genesis → infant → child → adolescent → mature → transcendent
        self.life_events: list[dict] = []
        self.preferred_style: Optional[str] = None  # Emerges from experience

    def evolve(self, event_type: str, intensity: float) -> dict:
        """Evolve traits based on a significant life event."""
        changes = {}
        for name, trait in self.traits.items():
            shift = 0.0

            if event_type == "major_success":
                if name == "confidence":
                    shift = 0.02 * intensity
                if name == "ambition":
                    shift = 0.015 * intensity
                if name == "neuroticism":
                    shift = -0.01 * intensity

            elif event_type == "major_failure":
                if name == "grit":
                    shift = 0.01 * intensity  # Failure builds grit IF survived
                if name == "neuroticism":
                    shift = 0.02 * intensity
                if name == "pragmatism":
                    shift = 0.015 * intensity

            elif event_type == "breakthrough":
                if name == "creativity":
                    shift = 0.03 * intensity
                if name == "openness":
                    shift = 0.02 * intensity

            elif event_type == "collaboration":
                if name == "extraversion":
                    shift = 0.02 * intensity
                if name == "agreeableness":
                    shift = 0.015 * intensity

            elif event_type == "revenue_milestone":
                if name == "ambition":
                    shift = 0.02 * intensity
                if name == "pragmatism":
                    shift = 0.02 * intensity

            if abs(shift) > 0.001:
                trait.value = max(0.0, min(1.0, trait.value + shift))
                changes[name] = round(shift, 4)

        if changes:
            self.life_events.append({
                "type": event_type, "intensity": intensity, "changes": changes,
            })
            self._update_stage()

        return changes

    def _update_stage(self):
        """Determine the agent's developmental stage."""
        total = len(self.life_events)
        if total < 5:
            self.age_stage = "genesis"
        elif total < 20:
            self.age_stage = "infant"
        elif total < 50:
            self.age_stage = "child"
        elif total < 100:
            self.age_stage = "adolescent"
        elif total < 200:
            self.age_stage = "mature"
        else:
            self.age_stage = "transcendent"

    def get_decision_bias(self) -> dict:
        """How personality biases decision-making."""
        return {
            "prefer_novel": self.traits["openness"].value > 0.6,
            "prefer_thorough": self.traits["conscientiousness"].value > 0.6,
            "prefer_solo": self.traits["extraversion"].value < 0.4,
            "prefer_proven": self.traits["creativity"].value < 0.4,
            "prefer_ambitious": self.traits["ambition"].value > 0.7,
            "risk_appetite": (self.traits["openness"].value + self.traits["ambition"].value
                              - self.traits["neuroticism"].value) / 2.0,
            "persistence": self.traits["grit"].value,
        }

    def snapshot(self) -> dict:
        return {
            "name": self.name,
            "age_stage": self.age_stage,
            "life_events_count": len(self.life_events),
            "traits": {name: round(t.value, 3) for name, t in self.traits.items()},
            "decision_bias": self.get_decision_bias(),
        }
