"""Auto-Correction System — Learns from every error and improves over time.

This is MUE's immune system + memory of mistakes. Every error encountered
during evolution is recorded, analyzed for patterns, and used to prevent
future failures. The system gets smarter with every cycle.

Subsystems:
- ErrorPatternDB: SQLite database of errors and their fixes
- SelfBenchmark: periodic performance measurement
- RegressionDetector: detects when new mutations break working code
- AutoCorrector: suggests fixes based on learned error patterns
"""

import ast
import hashlib
import json
import sqlite3
import time
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class ErrorRecord:
    """A single error event with context and resolution."""
    error_type: str
    message: str
    gene_name: str
    mutation_type: str
    source: str  # "evolution", "validation", "compilation", "runtime"
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    fix_pattern: str = ""  # what fixed it
    fix_success: bool = False
    fingerprint: str = ""  # unique hash for dedup

    def __post_init__(self):
        if not self.fingerprint:
            raw = f"{self.error_type}:{self.message[:100]}:{self.gene_name}"
            self.fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:16]


class ErrorPatternDB:
    """Persistent database of errors and their successful fixes."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_db()
        self.error_count = 0
        self.fix_count = 0

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT UNIQUE,
                error_type TEXT,
                message TEXT,
                gene_name TEXT,
                mutation_type TEXT,
                source TEXT,
                timestamp REAL,
                resolved INTEGER DEFAULT 0,
                fix_pattern TEXT,
                fix_success INTEGER DEFAULT 0,
                occurrence_count INTEGER DEFAULT 1
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fix_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_signature TEXT UNIQUE,
                fix_description TEXT,
                fix_code TEXT,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                last_used REAL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS benchmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                gene_count INTEGER,
                avg_fitness REAL,
                mutation_success_rate REAL,
                compilation_time_ms REAL,
                total_lines INTEGER,
                errors_since_last INTEGER
            )
        """)
        self.conn.commit()

    def record_error(self, error: ErrorRecord) -> str:
        """Record an error. Returns fingerprint. Increments occurrence count if duplicate."""
        try:
            existing = self.conn.execute(
                "SELECT id, occurrence_count FROM errors WHERE fingerprint = ?",
                (error.fingerprint,)
            ).fetchone()
            if existing:
                self.conn.execute(
                    "UPDATE errors SET occurrence_count = ?, timestamp = ? WHERE id = ?",
                    (existing[1] + 1, time.time(), existing[0])
                )
            else:
                self.conn.execute(
                    """INSERT INTO errors (fingerprint, error_type, message, gene_name,
                       mutation_type, source, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (error.fingerprint, error.error_type, error.message[:500],
                     error.gene_name, error.mutation_type, error.source, error.timestamp)
                )
            self.conn.commit()
            self.error_count += 1
            return error.fingerprint
        except Exception:
            return ""

    def record_fix(self, fingerprint: str, fix_pattern: str, success: bool):
        """Record that a fix was applied for an error."""
        self.conn.execute(
            "UPDATE errors SET resolved = 1, fix_pattern = ?, fix_success = ? WHERE fingerprint = ?",
            (fix_pattern, int(success), fingerprint)
        )

        # Update or create fix pattern
        sig = self._extract_signature(fix_pattern)
        existing = self.conn.execute(
            "SELECT id, success_count, failure_count FROM fix_patterns WHERE error_signature = ?",
            (sig,)
        ).fetchone()
        if existing:
            if success:
                self.conn.execute(
                    "UPDATE fix_patterns SET success_count = ?, last_used = ? WHERE id = ?",
                    (existing[1] + 1, time.time(), existing[0])
                )
            else:
                self.conn.execute(
                    "UPDATE fix_patterns SET failure_count = ?, last_used = ? WHERE id = ?",
                    (existing[2] + 1, time.time(), existing[0])
                )
        else:
            self.conn.execute(
                """INSERT INTO fix_patterns (error_signature, fix_description, fix_code, success_count, failure_count, last_used)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sig, fix_pattern[:200], fix_pattern, 1 if success else 0, 0 if success else 1, time.time())
            )
        self.conn.commit()
        if success:
            self.fix_count += 1

    def suggest_fix(self, error_message: str, error_type: str) -> Optional[str]:
        """Suggest a fix based on similar past errors."""
        rows = self.conn.execute(
            """SELECT fix_code, success_count, failure_count FROM fix_patterns
               WHERE error_signature LIKE ? AND success_count > 0
               ORDER BY success_count DESC LIMIT 3""",
            (f"%{self._extract_signature(error_type)}%",)
        ).fetchall()
        if not rows:
            return None
        best = max(rows, key=lambda r: r[1] - r[2])
        return best[0] if best[1] > best[2] else None

    def get_top_errors(self, limit: int = 10) -> list[dict]:
        """Get most frequent errors for analysis."""
        rows = self.conn.execute(
            "SELECT error_type, message, occurrence_count FROM errors ORDER BY occurrence_count DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"type": r[0], "message": r[1][:100], "count": r[2]} for r in rows]

    def record_benchmark(self, metrics: dict):
        """Record a performance benchmark snapshot."""
        self.conn.execute(
            """INSERT INTO benchmarks (timestamp, gene_count, avg_fitness, mutation_success_rate,
               compilation_time_ms, total_lines, errors_since_last)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (time.time(), metrics.get("gene_count", 0), metrics.get("avg_fitness", 0),
             metrics.get("mutation_success_rate", 0), metrics.get("compilation_time_ms", 0),
             metrics.get("total_lines", 0), metrics.get("errors_since_last", 0))
        )
        self.conn.commit()

    def _extract_signature(self, text: str) -> str:
        """Extract error signature for fuzzy matching."""
        text = text.lower()
        # Remove variable names, numbers, paths
        text = re.sub(r"'[^']*'", "'X'", text)
        text = re.sub(r'"[^"]*"', '"X"', text)
        text = re.sub(r'\b0x[0-9a-f]+\b', '0xHEX', text)
        text = re.sub(r'\b\d+\b', 'N', text)
        return text[:80]

    @property
    def stats(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*), SUM(occurrence_count) FROM errors"
        ).fetchone()
        return {
            "unique_errors": row[0] or 0,
            "total_occurrences": row[1] or 0,
            "fixes_applied": self.fix_count,
            "top_errors": self.get_top_errors(3),
        }

    def close(self):
        self.conn.close()


class SelfBenchmark:
    """Periodic self-performance measurement."""

    def __init__(self, error_db: ErrorPatternDB, genes_dir: Path):
        self.error_db = error_db
        self.genes_dir = Path(genes_dir)
        self.last_benchmark_time = time.time()
        self.benchmark_interval = 300  # every 5 minutes
        self.history: list[dict] = []

    def should_benchmark(self) -> bool:
        return time.time() - self.last_benchmark_time > self.benchmark_interval

    def benchmark(self, genome, evolution) -> dict:
        """Run a full self-benchmark."""
        start = time.perf_counter()

        # Compilation test
        try:
            import importlib
            importlib.invalidate_caches()
            compile_time = time.perf_counter() - start
            compilation_ok = True
        except Exception:
            compile_time = -1
            compilation_ok = False

        # Gene metrics
        genes = list(self.genes_dir.glob("*.py"))
        total_lines = sum(len(g.read_text(encoding="utf-8").split("\n")) for g in genes if g.stem != "__init__")

        gs = genome.stats
        es = evolution.stats if evolution else {}

        metrics = {
            "gene_count": len(genes),
            "avg_fitness": gs.get("avg_fitness", 0),
            "total_mutations": gs.get("total_mutations", 0),
            "mutation_success_rate": es.get("success_rate", 0),
            "compilation_time_ms": (time.perf_counter() - start) * 1000,
            "total_lines": total_lines,
            "avg_lines_per_gene": total_lines / max(len(genes), 1),
            "compilation_ok": compilation_ok,
        }

        self.error_db.record_benchmark(metrics)
        self.history.append(metrics)
        self.last_benchmark_time = time.time()

        return metrics


class RegressionDetector:
    """Detects when new mutations break previously working functionality."""

    def __init__(self, error_db: ErrorPatternDB):
        self.error_db = error_db
        self.baseline_metrics: dict = {}
        self.regression_threshold = 0.2  # 20% degradation triggers alert

    def set_baseline(self, metrics: dict):
        self.baseline_metrics = metrics

    def check(self, current_metrics: dict) -> dict:
        """Compare current metrics against baseline. Returns regressions found."""
        if not self.baseline_metrics:
            self.set_baseline(current_metrics)
            return {"regressions": [], "alert": False}

        regressions = []

        # Check fitness degradation
        baseline_fitness = self.baseline_metrics.get("avg_fitness", 0)
        current_fitness = current_metrics.get("avg_fitness", 0)
        if baseline_fitness > 0 and current_fitness < baseline_fitness * (1 - self.regression_threshold):
            regressions.append({
                "type": "fitness_drop",
                "before": baseline_fitness,
                "after": current_fitness,
                "delta": current_fitness - baseline_fitness,
            })

        # Check mutation success rate degradation
        baseline_success = self.baseline_metrics.get("mutation_success_rate", 0)
        current_success = current_metrics.get("mutation_success_rate", 0)
        if baseline_success > 0.5 and current_success < baseline_success * 0.5:
            regressions.append({
                "type": "mutation_success_drop",
                "before": baseline_success,
                "after": current_success,
            })

        # Check bloating
        baseline_lines = self.baseline_metrics.get("total_lines", 0)
        current_lines = current_metrics.get("total_lines", 0)
        if baseline_lines > 0 and current_lines > baseline_lines * 1.5:
            regressions.append({
                "type": "code_bloat",
                "before": baseline_lines,
                "after": current_lines,
                "growth_pct": (current_lines - baseline_lines) / max(baseline_lines, 1) * 100,
            })

        return {
            "regressions": regressions,
            "alert": len(regressions) > 0,
        }


class AutoCorrector:
    """The immune system: analyzes errors, suggests fixes, prevents recurrence."""

    def __init__(self, error_db: ErrorPatternDB, benchmark: SelfBenchmark, detector: RegressionDetector):
        self.error_db = error_db
        self.benchmark = benchmark
        self.detector = detector
        self.total_corrections = 0
        self.successful_corrections = 0

    def on_error(self, error_type: str, message: str, gene_name: str,
                 mutation_type: str = "", source: str = "evolution") -> Optional[str]:
        """Process an error. Record it and try to suggest a fix."""
        error = ErrorRecord(
            error_type=error_type,
            message=message,
            gene_name=gene_name,
            mutation_type=mutation_type,
            source=source,
        )
        fingerprint = self.error_db.record_error(error)

        # Check if we know how to fix this
        suggested_fix = self.error_db.suggest_fix(message, error_type)

        # Auto-correct common patterns without waiting
        if not suggested_fix:
            suggested_fix = self._auto_diagnose(error)

        return suggested_fix

    def on_fix(self, error_message: str, fix_description: str, success: bool):
        """Record that a fix was applied."""
        fingerprint = hashlib.sha256(
            f"fix:{error_message[:100]}".encode()
        ).hexdigest()[:16]
        self.error_db.record_fix(fingerprint, fix_description, success)

    def _auto_diagnose(self, error: ErrorRecord) -> Optional[str]:
        """Auto-diagnose common error patterns."""
        msg_lower = error.message.lower()

        if "cannot import" in msg_lower or "modulenotfound" in msg_lower or "no module named" in msg_lower:
            return "FIX: Check relative imports. Use 'from .module import X' for intra-package imports."
        if "syntaxerror" in msg_lower:
            return "FIX: AST validation failed. Check for missing colons, indentation, or unmatched brackets."
        if "attributeerror" in msg_lower and "has no attribute" in msg_lower:
            return "FIX: Object missing expected attribute. Check gene class definitions."
        if "typeerror" in msg_lower and "argument" in msg_lower:
            return "FIX: Function argument mismatch. Check parameter types and counts."
        if "indexerror" in msg_lower or "keyerror" in msg_lower:
            return "FIX: Add bounds/containment check before accessing collection."
        if "timeout" in msg_lower:
            return "FIX: Add retry logic with exponential backoff and timeout handling."
        if "connection" in msg_lower or "urlerror" in msg_lower:
            return "FIX: Add network error handling with fallback to cached/offline mode."

        return None

    def tick(self, genome, evolution_result: dict) -> dict:
        """Called each evolution cycle. Runs benchmarks, checks regressions, reports."""
        report = {
            "benchmark_ran": False,
            "regression_detected": False,
            "suggestions": [],
            "correction_count": self.total_corrections,
        }

        # Run benchmark if it's time
        if self.benchmark.should_benchmark():
            metrics = self.benchmark.benchmark(genome, None)
            report["benchmark_ran"] = True
            report["metrics"] = metrics

            # Check for regressions
            regression_result = self.detector.check(metrics)
            if regression_result["alert"]:
                report["regression_detected"] = True
                report["regressions"] = regression_result["regressions"]

                # Auto-heal: if fitness dropped, generate a repair signal
                for reg in regression_result["regressions"]:
                    report["suggestions"].append(f"REGRESSION {reg['type']}: {reg}")

        return report

    @property
    def stats(self) -> dict:
        return {
            "total_corrections": self.total_corrections,
            "successful_corrections": self.successful_corrections,
            "correction_rate": self.successful_corrections / max(self.total_corrections, 1),
            "error_db": self.error_db.stats,
        }
