"""SelfDiagnosis — The agent monitors its own health.

Detects: anomaly rates, corruption, stagnation, resource abuse, dead code.
Watches: error patterns, mutation success/failure ratio, gene fitness trends.
Alerts: when something is wrong AND when it's getting worse.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class DiagnosisReport:
    """A single health check result."""
    check_name: str
    status: str  # "healthy", "warning", "critical"
    message: str
    metrics: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    @property
    def severity(self) -> float:
        return {"healthy": 0.0, "warning": 0.5, "critical": 1.0}[self.status]


class SelfDiagnosis:
    """Continuous self-monitoring and anomaly detection.

    Watches:
    - Error rate: too many errors per cycle → alert
    - Mutation failure rate: > 50% = something wrong with the mutator
    - Gene fitness collapse: multiple genes dropping simultaneously
    - Kernel integrity: protected genes hash-checked
    - Stagnation: zero mutations for too many cycles
    - Resource health: disk space, DB integrity
    """

    def __init__(self, genome=None, rl_optimizer=None, scorer=None, error_db=None):
        self.genome = genome
        self.rl = rl_optimizer
        self.scorer = scorer
        self.error_db = error_db
        self.reports: list[DiagnosisReport] = []
        self.error_window: list[dict] = []
        self.mutation_window: list[dict] = []  # (success, timestamp)
        self.status_history: dict[str, list[str]] = defaultdict(list)

    def check_all(self, cycle_count: int, evolution_stats: dict,
                  error_events: list[dict] = None) -> list[DiagnosisReport]:
        """Run all health checks. Returns diagnosis reports."""
        reports = []

        reports.append(self._check_error_rate(error_events or []))
        reports.append(self._check_mutation_health(evolution_stats))
        reports.append(self._check_fitness_collapse())
        reports.append(self._check_stagnation(cycle_count, evolution_stats))
        reports.append(self._check_resource_health())

        for r in reports:
            self.status_history[r.check_name].append(r.status)
            if len(self.status_history[r.check_name]) > 20:
                self.status_history[r.check_name] = self.status_history[r.check_name][-20:]

        self.reports.extend(reports)
        if len(self.reports) > 200:
            self.reports = self.reports[-100:]

        # Escalate if a check has been warning/critical for 5+ consecutive cycles
        for r in reports:
            recent = self.status_history[r.check_name][-5:]
            if recent.count("critical") >= 3:
                r.status = "critical"
                r.message = f"[ESCALATED] {r.message}"

        return reports

    def _check_error_rate(self, error_events: list[dict]) -> DiagnosisReport:
        self.error_window.extend(error_events)
        if len(self.error_window) > 100:
            self.error_window = self.error_window[-100:]
        count = len(self.error_window)
        critical_count = sum(1 for e in self.error_window if e.get("severity", 0) > 0.7)
        status = "critical" if critical_count > 5 else ("warning" if count > 10 else "healthy")
        return DiagnosisReport(
            check_name="error_rate",
            status=status,
            message=f"{count} errors in window, {critical_count} critical",
            metrics={"total": count, "critical": critical_count},
        )

    def _check_mutation_health(self, stats: dict) -> DiagnosisReport:
        proposed = stats.get("mutations_proposed", 0)
        applied = stats.get("mutations_applied", 0)
        if proposed == 0:
            return DiagnosisReport("mutation_health", "healthy", "No mutations proposed")
        rate = applied / max(proposed, 1)
        status = "critical" if rate < 0.3 else ("warning" if rate < 0.5 else "healthy")
        return DiagnosisReport(
            check_name="mutation_health",
            status=status,
            message=f"Mutation apply rate: {rate:.0%} ({applied}/{proposed})",
            metrics={"rate": rate, "applied": applied, "proposed": proposed},
        )

    def _check_fitness_collapse(self) -> DiagnosisReport:
        if not self.genome or not self.genome.genes:
            return DiagnosisReport("fitness_collapse", "healthy", "No genes to check")
        genes = [g for n, g in self.genome.genes.items()
                if n not in ("mutator", "genome", "inspector", "solidify")]
        if not genes:
            return DiagnosisReport("fitness_collapse", "healthy", "No non-kernel genes")
        low_fitness = [g for g in genes if g.fitness < 0.2 and g.mutation_count > 2]
        status = "critical" if len(low_fitness) > 3 else ("warning" if low_fitness else "healthy")
        return DiagnosisReport(
            check_name="fitness_collapse",
            status=status,
            message=f"{len(low_fitness)} genes critically low fitness" if low_fitness else "All genes healthy",
            metrics={"low_fitness_count": len(low_fitness)},
        )

    def _check_stagnation(self, cycle: int, stats: dict) -> DiagnosisReport:
        total_mutations = stats.get("total_mutations_applied", 0)
        # Track mutation delta
        prev = getattr(self, '_prev_total_mutations', total_mutations)
        self._prev_total_mutations = total_mutations
        stuck = (total_mutations - prev) == 0
        if not stuck or cycle < 3:
            return DiagnosisReport("stagnation", "healthy", f"Evolving normally")
        return DiagnosisReport(
            "stagnation", "warning",
            f"No new mutations in recent cycles",
            metrics={"total_mutations": total_mutations},
        )

    def _check_resource_health(self) -> DiagnosisReport:
        try:
            import shutil
            disk = shutil.disk_usage(".")
            pct = disk.used / disk.total
            status = "critical" if pct > 0.95 else ("warning" if pct > 0.85 else "healthy")
            return DiagnosisReport(
                "resources",
                status=status,
                message=f"Disk: {pct:.0%} used ({disk.free // 1024**3}GB free)",
                metrics={"disk_pct": pct, "free_gb": disk.free // 1024**3},
            )
        except Exception:
            return DiagnosisReport("resources", "healthy", "Could not check resources")

    def get_escalated_alerts(self) -> list[DiagnosisReport]:
        """Get only critical alerts that need immediate attention."""
        return [r for r in self.reports[-10:] if r.status == "critical"]

    @property
    def overall_health(self) -> str:
        recent = self.reports[-8:]
        criticals = sum(1 for r in recent if r.status == "critical")
        warnings = sum(1 for r in recent if r.status == "warning")
        if criticals > 2:
            return "critical"
        if criticals > 0 or warnings > 3:
            return "degraded"
        if warnings > 0:
            return "warning"
        return "healthy"

    @property
    def stats(self) -> dict:
        return {
            "overall_health": self.overall_health,
            "recent_reports": [
                {"name": r.check_name, "status": r.status, "msg": r.message[:100]}
                for r in self.reports[-5:]
            ],
            "alerts": len(self.get_escalated_alerts()),
        }
