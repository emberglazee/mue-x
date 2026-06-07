"""CycleAdapter — Auto-tune the evolution loop's rhythm and strategy.

The fixed 30-second cycle is naive. The agent should:
- Accelerate when mutations are succeeding (compound gains)
- Decelerate when stagnating (not burn resources on nothing)
- Switch strategies when the current one flatlines
- Adapt interval based on signal pressure
"""

import time
from dataclasses import dataclass, field


@dataclass
class CycleConfig:
    """Current evolution cycle configuration."""
    interval_seconds: float = 30.0
    strategy: str = "balanced"
    max_mutations_per_cycle: int = 3
    signal_severity_threshold: float = 0.2
    mutation_rate: float = 1.0  # Multiplier: 0.5 = half mutations, 2.0 = double
    last_modified: float = field(default_factory=time.time)


class CycleAdapter:
    """Adapts the evolution loop timing and strategy based on outcomes.

    Behavior rules:
    - Streak of 5+ successful mutations → accelerate (interval *= 0.8)
    - Streak of 3+ failed mutations → decelerate (interval *= 1.3)
    - 5 cycles with 0 mutations → change strategy
    - High signal pressure → increase mutation budget
    - Low signal pressure → decrease mutation budget
    - Resource throttle → respect mutation budget cap
    """

    STRATEGIES = ["balanced", "bold", "innovate", "harden", "repair-only", "explore"]

    def __init__(self, resource_monitor=None, base_strategy: str = "balanced"):
        self.config = CycleConfig(strategy=base_strategy)
        self.base_strategy = base_strategy
        self.resources = resource_monitor
        self.recent_outcomes: list[bool] = []  # True = success, False = failure
        self.strategy_history: dict[str, float] = {}  # strategy -> last_used timestamp
        self.cycle_history: list[dict] = []
        self.total_adaptations = 0

    def adapt(self, cycle_stats: dict) -> CycleConfig:
        """Analyze the last cycle's results and adapt for the next one."""
        mutations_applied = cycle_stats.get("mutations_applied", 0)
        mutations_proposed = cycle_stats.get("mutations_proposed", 0)
        signals = cycle_stats.get("signals_detected", 0)
        cycle_time_ms = cycle_stats.get("cycle_time_ms", 0)

        self.total_adaptations += 1

        # Track outcomes
        if mutations_applied > 0:
            self.recent_outcomes.append(True)
        elif mutations_proposed > 0:
            self.recent_outcomes.append(False)

        if len(self.recent_outcomes) > 20:
            self.recent_outcomes = self.recent_outcomes[-20:]

        # 1. Adapt interval based on success streak
        recent_5 = self.recent_outcomes[-5:]
        success_streak = sum(1 for x in recent_5 if x)
        failure_streak = sum(1 for x in recent_5 if not x)

        if success_streak >= 4:
            self.config.interval_seconds *= 0.85  # Speed up — we're on a roll
            self.config.mutation_rate = min(2.0, self.config.mutation_rate * 1.1)
        elif failure_streak >= 3:
            self.config.interval_seconds *= 1.25  # Slow down — something's wrong
            self.config.mutation_rate = max(0.3, self.config.mutation_rate * 0.8)
        else:
            # Gradually return to baseline
            if self.config.interval_seconds > 40:
                self.config.interval_seconds *= 0.95
            if self.config.mutation_rate < 0.9:
                self.config.mutation_rate *= 1.05

        # Clamp interval
        self.config.interval_seconds = max(5.0, min(120.0, self.config.interval_seconds))

        # 2. Adapt strategy if stagnating
        if mutations_applied == 0 and mutations_proposed == 0:
            stuck_cycles = sum(1 for c in self.cycle_history[-10:]
                             if c.get("mutations_applied", 0) == 0)
            if stuck_cycles >= 5:
                self._rotate_strategy()

        # 3. Adapt mutation budget based on signal pressure
        if signals > 5:
            self.config.max_mutations_per_cycle = min(5, self.config.max_mutations_per_cycle + 1)
        elif signals == 0:
            self.config.max_mutations_per_cycle = max(1, self.config.max_mutations_per_cycle - 1)

        if signals > 0:
            self.config.signal_severity_threshold = max(0.1, 0.2 - signals * 0.02)

        # 4. Respect resource throttle
        if self.resources:
            if self.resources.throttle_level >= 1:
                self.config.max_mutations_per_cycle = min(
                    self.config.max_mutations_per_cycle,
                    self.resources.mutation_budget,
                )
            self.config.interval_seconds = max(
                self.config.interval_seconds,
                self.resources.get_recommended_interval(10.0),
            )

        self.cycle_history.append(cycle_stats)
        if len(self.cycle_history) > 100:
            self.cycle_history = self.cycle_history[-50:]

        self.config.last_modified = time.time()
        return self.config

    def _rotate_strategy(self):
        """Switch to the next strategy in the rotation."""
        current_idx = self.STRATEGIES.index(self.config.strategy) if self.config.strategy in self.STRATEGIES else 0
        next_idx = (current_idx + 1) % len(self.STRATEGIES)
        self.config.strategy = self.STRATEGIES[next_idx]
        self.strategy_history[self.config.strategy] = time.time()

    def get_adaptive_interval(self) -> float:
        """Get the current recommended cycle interval."""
        return self.config.interval_seconds

    def get_adaptive_strategy(self) -> str:
        return self.config.strategy

    def get_mutation_budget(self) -> int:
        return self.config.max_mutations_per_cycle

    @property
    def stats(self) -> dict:
        return {
            "interval": round(self.config.interval_seconds, 1),
            "strategy": self.config.strategy,
            "mutation_budget": self.config.max_mutations_per_cycle,
            "mutation_rate": round(self.config.mutation_rate, 2),
            "adaptations": self.total_adaptations,
            "success_streak": sum(1 for x in self.recent_outcomes[-5:] if x),
        }
