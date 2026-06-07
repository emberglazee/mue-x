"""Real Feedback Loop — Measures task outcomes to score gene performance.

This is the key insight: mutations without feedback are random walks.
With this module, Mue tracks which genes contribute to successful tasks
and prioritizes mutations that improve real-world performance.

Every task Mue performs is recorded. Every gene involved is scored.
Mutations that produce better outcomes are reinforced. Bad ones are reverted.
"""

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TaskRecord:
    """A single task execution with outcome scoring."""
    task_id: str
    description: str
    genes_involved: list[str]
    success: bool
    duration_ms: float
    complexity: float  # 0-1
    impact_score: float  # 0-1: how much this task mattered
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class GenePerformance:
    """Aggregated performance metrics for one gene."""
    gene_name: str
    tasks_involved: int = 0
    successes: int = 0
    failures: int = 0
    avg_duration_ms: float = 0.0
    avg_complexity: float = 0.0
    total_impact: float = 0.0
    last_score: float = 0.0
    score_trend: list[float] = field(default_factory=list)  # last 10 scores

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.tasks_involved, 1)

    @property
    def performance_score(self) -> float:
        """Composite score: success rate * impact * complexity bonus."""
        base = self.success_rate * (0.5 + 0.5 * self.total_impact / max(self.tasks_involved, 1))
        complexity_bonus = min(0.3, self.avg_complexity * 0.3)
        return min(1.0, base + complexity_bonus)


class TaskScorer:
    """Records tasks, scores genes, and feeds back to evolution.

    This is the foundation of Mue's REAL intelligence improvement.
    Without this, mutations are just random AST changes.
    With this, Mue learns what works and doubles down.
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or Path("mue_feedback.db")
        self._init_db()
        self.task_history: list[TaskRecord] = []
        self.gene_performance: dict[str, GenePerformance] = {}
        self._load_gene_scores()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                description TEXT,
                genes_involved TEXT,  -- JSON array
                success INTEGER,
                duration_ms REAL,
                complexity REAL,
                impact_score REAL,
                error_message TEXT,
                timestamp REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gene_scores (
                gene_name TEXT PRIMARY KEY,
                tasks_involved INTEGER DEFAULT 0,
                successes INTEGER DEFAULT 0,
                failures INTEGER DEFAULT 0,
                avg_duration_ms REAL DEFAULT 0,
                avg_complexity REAL DEFAULT 0,
                total_impact REAL DEFAULT 0,
                last_score REAL DEFAULT 0,
                score_trend TEXT DEFAULT '[]'  -- JSON array
            )
        """)
        conn.commit()
        conn.close()

    def _load_gene_scores(self):
        try:
            conn = sqlite3.connect(str(self.db_path))
            rows = conn.execute("SELECT * FROM gene_scores").fetchall()
            for row in rows:
                gp = GenePerformance(
                    gene_name=row[0],
                    tasks_involved=row[1],
                    successes=row[2],
                    failures=row[3],
                    avg_duration_ms=row[4],
                    avg_complexity=row[5],
                    total_impact=row[6],
                    last_score=row[7],
                    score_trend=json.loads(row[8]) if row[8] else [],
                )
                self.gene_performance[row[0]] = gp
            conn.close()
        except Exception:
            pass

    def record_task(self, task: TaskRecord):
        """Record a task outcome. Updates gene scores."""
        self.task_history.append(task)
        if len(self.task_history) > 500:
            self.task_history = self.task_history[-500:]

        # Update gene performance
        for gene_name in task.genes_involved:
            if gene_name not in self.gene_performance:
                self.gene_performance[gene_name] = GenePerformance(gene_name=gene_name)

            gp = self.gene_performance[gene_name]
            gp.tasks_involved += 1
            if task.success:
                gp.successes += 1
            else:
                gp.failures += 1

            # Rolling averages
            n = gp.tasks_involved
            gp.avg_duration_ms = (gp.avg_duration_ms * (n - 1) + task.duration_ms) / n
            gp.avg_complexity = (gp.avg_complexity * (n - 1) + task.complexity) / n
            gp.total_impact += task.impact_score

            # Score trend (last 10)
            gp.score_trend.append(gp.performance_score)
            if len(gp.score_trend) > 10:
                gp.score_trend = gp.score_trend[-10:]
            gp.last_score = gp.performance_score

        # Persist
        self._save_task(task)
        for gene_name in task.genes_involved:
            self._save_gene_score(gene_name)

    def _save_task(self, task: TaskRecord):
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "INSERT OR REPLACE INTO tasks VALUES (?,?,?,?,?,?,?,?,?)",
                (task.task_id, task.description, json.dumps(task.genes_involved),
                 int(task.success), task.duration_ms, task.complexity,
                 task.impact_score, task.error_message, task.timestamp),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _save_gene_score(self, gene_name: str):
        gp = self.gene_performance.get(gene_name)
        if not gp:
            return
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                "INSERT OR REPLACE INTO gene_scores VALUES (?,?,?,?,?,?,?,?,?)",
                (gp.gene_name, gp.tasks_involved, gp.successes, gp.failures,
                 gp.avg_duration_ms, gp.avg_complexity, gp.total_impact,
                 gp.last_score, json.dumps(gp.score_trend[-10:])),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def get_mutation_priority(self, gene_name: str) -> float:
        """Higher score = this gene should be mutated MORE (it's important).
        Lower score = this gene should be mutated to IMPROVE (it's weak)."""
        gp = self.gene_performance.get(gene_name)
        if not gp:
            return 0.5  # Unknown — neutral priority
        if gp.tasks_involved < 3:
            return 0.5
        return gp.performance_score

    def get_weakest_genes(self, n: int = 3) -> list[str]:
        """Genes with lowest performance — need improvement."""
        scored = [(name, gp.performance_score)
                  for name, gp in self.gene_performance.items()
                  if gp.tasks_involved >= 2]
        scored.sort(key=lambda x: x[1])
        return [name for name, _ in scored[:n]]

    def get_strongest_genes(self, n: int = 3) -> list[str]:
        """Genes with highest performance — reinforce and protect."""
        scored = [(name, gp.performance_score)
                  for name, gp in self.gene_performance.items()
                  if gp.tasks_involved >= 2]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored[:n]]

    def get_reinforcement_signal(self, gene_name: str) -> dict:
        """Generate an evolution signal based on gene performance trend."""
        gp = self.gene_performance.get(gene_name)
        if not gp or len(gp.score_trend) < 3:
            return {"action": "neutral", "gene": gene_name, "score": 0.5}

        recent = gp.score_trend[-3:]
        trend = recent[-1] - recent[0]

        if trend > 0.1:
            return {"action": "reinforce", "gene": gene_name,
                    "score": gp.last_score, "message": f"Gene '{gene_name}' improving ({trend:+.2f}) — reinforce these mutations"}
        elif trend < -0.1:
            return {"action": "revert_pattern", "gene": gene_name,
                    "score": gp.last_score, "message": f"Gene '{gene_name}' degrading ({trend:+.2f}) — avoid recent mutation patterns"}
        else:
            return {"action": "explore", "gene": gene_name,
                    "score": gp.last_score, "message": f"Gene '{gene_name}' stable — explore new patterns"}

    @property
    def stats(self) -> dict:
        total_tasks = sum(gp.tasks_involved for gp in self.gene_performance.values())
        avg_score = (
            sum(gp.performance_score for gp in self.gene_performance.values())
            / max(len(self.gene_performance), 1)
        )
        return {
            "total_tasks_recorded": len(self.task_history),
            "total_gene_tasks": total_tasks,
            "genes_tracked": len(self.gene_performance),
            "avg_performance_score": round(avg_score, 3),
            "weakest_genes": self.get_weakest_genes(3),
            "strongest_genes": self.get_strongest_genes(3),
        }

    def close(self):
        pass  # SQLite connections are short-lived
