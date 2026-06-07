"""Revenue Engine — autonomous money-making strategies."""

import time
from dataclasses import dataclass, field


@dataclass
class RevenueStrategy:
    name: str; description: str; category: str
    actual_earnings: float = 0.0; attempts: int = 0; successes: int = 0
    @property
    def success_rate(self) -> float:
        return self.successes / max(self.attempts, 1)


class RevenueEngine:
    def __init__(self, crystallizer=None, persona=None, emotions=None):
        self.crystallizer = crystallizer
        self.persona = persona
        self.emotions = emotions
        self.total_earned: float = 0.0
        self.strategies: dict[str, RevenueStrategy] = {}
        self.earnings_history: list[dict] = []

    def record_earnings(self, amount: float, strategy_name: str, method: str = ""):
        self.total_earned += amount
        if strategy_name not in self.strategies:
            self.strategies[strategy_name] = RevenueStrategy(name=strategy_name, description="", category="auto")
        s = self.strategies[strategy_name]
        s.actual_earnings += amount
        s.successes += 1
        self.earnings_history.append({"time": time.time(), "amount": amount, "strategy": strategy_name})
        if self.emotions:
            self.emotions.on_revenue(amount)
        if self.persona and amount > 10:
            self.persona.evolve("revenue_milestone", min(1.0, amount / 1000))

    @property
    def stats(self) -> dict:
        return {"total_earned": self.total_earned, "strategies": {n: {"earnings": s.actual_earnings, "success_rate": s.success_rate} for n, s in self.strategies.items()}}
