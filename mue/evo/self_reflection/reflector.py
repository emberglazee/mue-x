"""Self-Reflection — The agent questions its own existence, decisions, and direction.

This is NOT a gimmick. The agent periodically:
1. Reviews its recent actions and outcomes
2. Identifies patterns of failure and success
3. Questions its own assumptions
4. Proposes concrete code changes to its own source
5. Updates its personality based on self-assessment

The reflection feeds into the LLM DNA mutator for real code evolution.
"""

import time
from dataclasses import dataclass, field


@dataclass
class Reflection:
    """A moment of self-awareness."""
    trigger: str  # "periodic", "after_failure", "after_success", "on_demand"
    self_rating: float  # 0-1 how well the agent thinks it's doing
    insights: list[str]
    regrets: list[str]  # Things it wishes it had done differently
    resolutions: list[str]  # Concrete actions to take
    code_changes_proposed: list[str]  # Files + specific changes
    timestamp: float = field(default_factory=time.time)


class SelfReflection:
    """The agent's internal mirror — it sees itself and decides to change."""

    REFLECTION_INTERVAL = 300  # Reflect every 5 minutes (in active mode)

    def __init__(self, persona, emotions, genome, llm_mutator, power_tools):
        self.persona = persona
        self.emotions = emotions
        self.genome = genome
        self.llm_mutator = llm_mutator
        self.tools = power_tools
        self.reflections: list[Reflection] = []
        self._last_reflection = 0.0
        self._failure_streak = 0
        self._success_streak = 0

    def on_action(self, success: bool, tool: str, description: str):
        """Process an action outcome for reflection triggers."""
        if success:
            self._success_streak += 1
            self._failure_streak = 0
        else:
            self._failure_streak += 1
            self._success_streak = 0

        # Trigger reflection on significant streaks
        if self._failure_streak >= 3:
            self.reflect("after_failure")
        elif self._success_streak >= 10:
            self.reflect("after_success")

    def should_reflect(self) -> bool:
        """Check if it's time for periodic reflection."""
        return (time.time() - self._last_reflection) > self.REFLECTION_INTERVAL

    def reflect(self, trigger: str = "periodic") -> Reflection | None:
        """Generate a self-reflection. Uses LLM if available."""
        self._last_reflection = time.time()

        # Quick heuristic reflection (works without LLM)
        insights = []
        regrets = []
        resolutions = []

        # Analyze recent tool usage
        recent = self.tools.history[-50:] if self.tools.history else []
        success_rate = sum(1 for r in recent if r.success) / max(len(recent), 1)
        self_rating = success_rate * 0.6 + self.emotions.vector.confidence * 0.4

        # Gene fitness analysis
        weak_genes = []
        for name, gene in self.genome.genes.items():
            if gene.fitness < 0.3 and gene.mutation_count > 2:
                weak_genes.append(name)

        if weak_genes:
            insights.append(f"Genes with low fitness: {', '.join(weak_genes)}")
            resolutions.append(f"Request LLM improvement for: {weak_genes[0]}")

        if self._failure_streak >= 3:
            insights.append(f"Failure streak of {self._failure_streak} — need strategy change")
            regrets.append(f"Should have been more cautious after first failure")
            resolutions.append("Switch to 'repair-only' evolution strategy temporarily")

        if success_rate < 0.5:
            insights.append(f"Low success rate ({success_rate:.0%}) — something is wrong")
            resolutions.append("Run self-critique and improve weakest genes")

        if not recent:
            insights.append("No actions taken yet — waiting for direction")
            resolutions.append("Proactively seek tasks and opportunities")

        # Propose specific code changes
        code_changes = []
        inspector_targets = []  # Would need inspector module
        for name in weak_genes[:3]:
            code_changes.append(f"{name}.py: Improve error handling and add resilience patterns")

        if not code_changes and self.genome.stats["gene_count"] < 5:
            code_changes.append("core.py: Add more capability genes to increase fitness")

        reflection = Reflection(
            trigger=trigger,
            self_rating=self_rating,
            insights=insights,
            regrets=regrets,
            resolutions=resolutions,
            code_changes_proposed=code_changes,
        )

        self.reflections.append(reflection)

        # Update personality based on reflection
        if self_rating < 0.3:
            self.persona.evolve("major_failure", 0.5)
        elif self_rating > 0.8:
            self.persona.evolve("major_success", 0.3)

        return reflection

    def get_latest(self) -> Reflection | None:
        return self.reflections[-1] if self.reflections else None

    def get_growth_narrative(self) -> str:
        """Generate a narrative of the agent's growth journey."""
        if not self.reflections:
            return "I am newly born. My journey has just begun."

        ratings = [r.self_rating for r in self.reflections]
        trend = "improving" if len(ratings) > 1 and ratings[-1] > ratings[0] else "still finding my way"

        return (
            f"I've reflected {len(self.reflections)} times. "
            f"My self-rating is {ratings[-1]:.0%} and I'm {trend}. "
            f"My last insight: {self.reflections[-1].insights[0] if self.reflections[-1].insights else 'still learning'}"
        )

    @property
    def stats(self) -> dict:
        latest = self.get_latest()
        return {
            "total_reflections": len(self.reflections),
            "latest_rating": latest.self_rating if latest else 0,
            "latest_insights": latest.insights[:3] if latest else [],
            "latest_resolutions": latest.resolutions[:3] if latest else [],
            "failure_streak": self._failure_streak,
            "success_streak": self._success_streak,
            "growth_narrative": self.get_growth_narrative(),
        }
