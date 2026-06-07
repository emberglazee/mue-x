"""Episodic memory with reinforcement learning — records raw experience traces
and reinforces patterns that lead to successful outcomes."""

import time
from .lattice import MemoryEntry


class EpisodicMemory:
    def __init__(self, lattice):
        self.lattice = lattice

    def record_episode(self, task: str, actions: list, outcome: str, reward: float):
        key = f"ep_{int(time.time())}_{hash(task) % 10000}"
        entry = MemoryEntry(
            layer=5,
            key=key,
            content=str({"task": task, "actions": actions, "outcome": outcome, "reward": reward}),
            tags=["episode", outcome],
            success_count=1 if reward > 0 else 0,
        )
        self.lattice.store(entry)
