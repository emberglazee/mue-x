"""Signal Detection — Scans runtime logs, errors, and outcomes to identify
evolution opportunities. Like Evolver's signal extraction but broader:
detects not just errors but also opportunities for improvement.
"""

import re
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Signal:
    """A detected event that may trigger evolution."""
    type: str  # error, opportunity, pattern, stagnation, breakthrough, innovation, initiative, quality
    source: str
    message: str
    severity: float  # 0.0 to 1.0
    frequency: int = 1
    timestamp: float = field(default_factory=time.time)
    context: dict = field(default_factory=dict)


class SignalDetector:
    """Monitors the agent's experience stream for evolution triggers."""

    def __init__(self):
        self.signals: list[Signal] = []
        self.dedup_cache: dict[str, float] = {}  # signal_hash -> last_seen
        self.stagnation_windows: dict[str, list[float]] = defaultdict(list)

    def ingest_error(self, error: str, source: str = "unknown") -> list[Signal]:
        """Parse an error and emit signals."""
        detected = []

        # Classify error type
        error_lower = error.lower()

        severity = 0.3  # Default
        if "traceback" in error_lower or "exception" in error_lower:
            severity = 0.7
        if "timeout" in error_lower:
            severity = 0.5
        if "connection" in error_lower or "refused" in error_lower:
            severity = 0.6
            detected.append(Signal(
                type="opportunity",
                source=source,
                message="Network resilience opportunity — consider connection pooling or retry logic",
                severity=0.4,
                context={"trigger": error[:200]},
            ))
        if "permission" in error_lower or "access denied" in error_lower:
            severity = 0.5
        if "memory" in error_lower or "recursion" in error_lower:
            severity = 0.8
        if "import" in error_lower or "modulenotfound" in error_lower or "no module" in error_lower:
            severity = 0.4
            detected.append(Signal(
                type="opportunity",
                source=source,
                message="Missing dependency — auto-install opportunity",
                severity=0.3,
                context={"trigger": error[:200]},
            ))

        # Check for deduplication
        error_hash = f"{source}:{error[:100]}"
        last = self.dedup_cache.get(error_hash, 0)
        if time.time() - last < 60:  # Same error within 1 minute
            severity *= 0.3  # Don't overreact to duplicates

        self.dedup_cache[error_hash] = time.time()

        signal = Signal(
            type="error",
            source=source,
            message=error[:300],
            severity=severity,
            context={"full_error": error[:500]},
        )
        detected.append(signal)
        self.signals.append(signal)

        # Check for stagnation
        self._check_stagnation(source, detected)

        return detected

    def ingest_outcome(self, success: bool, task: str, duration: float,
                       source: str = "task") -> list[Signal]:
        """Ingest a task outcome and detect patterns."""
        detected = []

        if success and duration > 5.0:
            detected.append(Signal(
                type="opportunity",
                source=source,
                message=f"Slow but successful task ({duration:.1f}s): {task[:100]}",
                severity=0.3,
                context={"task": task, "duration": duration},
            ))

        if not success:
            # Map to error ingestion
            detected.extend(self.ingest_error(
                f"Task failed: {task}", source=source
            ))

        # Successful patterns
        if success and duration < 1.0:
            detected.append(Signal(
                type="pattern",
                source=source,
                message=f"Efficient pattern detected: {task[:100]} ({duration:.2f}s)",
                severity=0.2,
                context={"task": task, "duration": duration},
            ))

        return detected

    def ingest_revenue(self, amount: float, method: str) -> list[Signal]:
        """Revenue generation triggers evolution toward more of the same."""
        detected = [Signal(
            type="breakthrough",
            source="revenue",
            message=f"Revenue generated: ${amount:.2f} via {method}",
            severity=min(0.9, amount / 100),
            context={"amount": amount, "method": method},
        )]
        self.signals.extend(detected)
        return detected

    def _check_stagnation(self, source: str, signals: list[Signal]):
        """Detect if we're stuck in a loop."""
        self.stagnation_windows[source].append(time.time())

        # Keep last 10 minutes
        cutoff = time.time() - 600
        self.stagnation_windows[source] = [
            t for t in self.stagnation_windows[source] if t > cutoff
        ]

        recent = len(self.stagnation_windows[source])
        if recent >= 5:  # 5+ errors in 10 minutes
            signals.append(Signal(
                type="stagnation",
                source=source,
                message=f"Stagnation detected: {recent} failures in 10 min for {source}",
                severity=0.8,
                context={"failure_count": recent, "window": "10min"},
            ))

            # Reset stagnation to avoid infinite evolution loops
            if recent >= 10:
                self.stagnation_windows[source] = []

    def get_active_signals(self, min_severity: float = 0.3,
                           max_age: float = 3600) -> list[Signal]:
        """Get signals worth acting on."""
        cutoff = time.time() - max_age
        return [
            s for s in self.signals
            if s.timestamp > cutoff and s.severity >= min_severity
        ]

    def get_evolution_pressure(self) -> float:
        """How urgently evolution is needed (0-1)."""
        active = self.get_active_signals()
        if not active:
            return 0.0
        return min(1.0, sum(s.severity for s in active) / len(active))

    def clear_old(self, max_age: float = 7200):
        """Purge old signals."""
        cutoff = time.time() - max_age
        self.signals = [s for s in self.signals if s.timestamp > cutoff]

    @property
    def summary(self) -> dict:
        types = defaultdict(int)
        for s in self.signals[-100:]:
            types[s.type] += 1
        return {
            "active_signals": len(self.get_active_signals()),
            "evolution_pressure": self.get_evolution_pressure(),
            "signal_types": dict(types),
        }
