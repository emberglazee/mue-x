"""ResourceMonitor — Track and adapt to system resource usage.

Monitors CPU, RAM, disk, and the agent's own mutation budget.
Alerts when resources are constrained and adjusts behavior.
"""

import os
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


@dataclass
class ResourceSnapshot:
    """A point-in-time resource measurement."""
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_mb: float = 0.0
    disk_percent: float = 0.0
    disk_free_gb: float = 0.0
    open_files: int = 0
    thread_count: int = 0
    timestamp: float = field(default_factory=time.time)


class ResourceMonitor:
    """Continuous resource monitoring with adaptive thresholds.

    When resources are constrained:
    - Reduce mutation rate (fewer per cycle)
    - Extend cycle interval (give system time to breathe)
    - Suspend non-essential subsystems (swarm, absorption)
    - Alert the meta-cognition layer

    Provides a mutation budget: how many mutations the agent can
    afford this cycle given current resource usage.
    """

    HIGH_CPU = 80.0
    HIGH_RAM = 85.0
    LOW_DISK_GB = 1.0

    def __init__(self, work_dir: Path = None):
        self.work_dir = work_dir or Path(".")
        self.history: list[ResourceSnapshot] = []
        self._monitor_thread: threading.Thread | None = None
        self._running = False
        self.throttle_level = 0  # 0=normal, 1=reduced, 2=minimal, 3=emergency
        self.mutation_budget = 5  # Max mutations per cycle
        self._debounce = 0  # Only snapshot every N calls

    def snapshot(self) -> ResourceSnapshot:
        """Take a current resource snapshot."""
        snap = ResourceSnapshot()

        if HAS_PSUTIL:
            try:
                snap.cpu_percent = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                snap.ram_percent = mem.percent
                snap.ram_used_mb = mem.used / (1024 * 1024)
                process = psutil.Process()
                snap.open_files = len(process.open_files())
                snap.thread_count = process.num_threads()
            except Exception:
                pass

        try:
            import shutil
            disk = shutil.disk_usage(str(self.work_dir))
            snap.disk_percent = (disk.used / disk.total) * 100
            snap.disk_free_gb = disk.free / (1024 ** 3)
        except Exception:
            pass

        self.history.append(snap)
        if len(self.history) > 100:
            self.history = self.history[-50:]
        return snap

    def assess(self) -> int:
        """Assess current resource state. Returns throttle level 0-3.
        Debounced: only takes full snapshot every 3rd call to avoid I/O overhead."""
        self._debounce += 1
        if self._debounce % 3 != 0:
            return self.throttle_level  # Return cached level
        snap = self.snapshot()

        issues = 0
        if snap.cpu_percent > self.HIGH_CPU:
            issues += 1
        if snap.ram_percent > self.HIGH_RAM:
            issues += 1
        if snap.disk_free_gb < self.LOW_DISK_GB:
            issues += 1

        if issues >= 3:
            self.throttle_level = 3
            self.mutation_budget = 0
        elif issues >= 2:
            self.throttle_level = 2
            self.mutation_budget = 1
        elif issues >= 1:
            self.throttle_level = 1
            self.mutation_budget = 2
        else:
            self.throttle_level = 0
            self.mutation_budget = 5

        return self.throttle_level

    def should_throttle(self, subsystem: str) -> bool:
        """Should a given subsystem be throttled or suspended?

        Critical subsystems (evolution, memory) are never fully suspended.
        Non-essential systems (swarm, absorption) suspend at level 2+.
        """
        if subsystem in ("evolution", "memory", "kernel"):
            return self.throttle_level >= 3
        if subsystem in ("swarm", "absorption", "self_reflection"):
            return self.throttle_level >= 2
        return self.throttle_level >= 1

    def get_recommended_interval(self, base_interval: float = 30.0) -> float:
        """Get recommended cycle interval based on resource state."""
        if self.throttle_level == 3:
            return base_interval * 4.0  # Emergency: slow way down
        if self.throttle_level == 2:
            return base_interval * 2.0
        if self.throttle_level == 1:
            return base_interval * 1.5
        return base_interval

    @property
    def stats(self) -> dict:
        latest = self.history[-1] if self.history else ResourceSnapshot()
        return {
            "throttle_level": self.throttle_level,
            "mutation_budget": self.mutation_budget,
            "cpu_pct": round(latest.cpu_percent, 1),
            "ram_pct": round(latest.ram_percent, 1),
            "disk_free_gb": round(latest.disk_free_gb, 1),
            "threads": latest.thread_count,
        }
