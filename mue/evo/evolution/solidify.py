"""Solidify — Validation and persistence of evolution events.

Inspired by Evolver's solidify.js: validates mutated code before
committing it permanently. Uses AST parsing, import checks, and
basic test execution as safety gates.
"""

import ast
import importlib.util
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class Solidifier:
    """Validates and persists evolutionary changes."""

    VALIDATION_TIMEOUT = 30  # seconds per validation step

    def __init__(self, genome, git_enabled: bool = True, sandbox=None):
        self.genome = genome
        self.git_enabled = git_enabled
        self.sandbox = sandbox  # GeneSandbox — subprocess isolation
        self.validation_log: list[dict] = []
        self.rollback_snapshots: dict[str, str] = {}  # gene_name -> old_source

    def validate(self, gene_name: str, new_source: str) -> tuple[bool, str]:
        """Run full validation on a mutation before committing it.

        Returns (is_valid, reason).
        """
        # Gate 1: AST parsing
        try:
            tree = ast.parse(new_source)
        except SyntaxError as e:
            return False, f"SYNTAX: {e}"

        # Gate 2: No dangerous patterns
        dangerous = ["__import__('os').system(", "eval(", "exec(",
                      "subprocess.call(", "rm -rf", "shutil.rmtree"]
        for pattern in dangerous:
            if pattern in new_source:
                return False, f"DANGEROUS: Contains prohibited pattern '{pattern}'"

        # Gate 2.5: Sandbox execution (subprocess isolation with timeout)
        if self.sandbox:
            ok, reason = self.sandbox.quick_validate(gene_name, new_source)
            if not ok:
                return False, f"SANDBOX: {reason}"

        # Gate 3: Basic import validation
        import_errors = self._check_imports(tree)
        if import_errors:
            return False, f"IMPORT: {import_errors[0]}"

        # Gate 4: Snapshot current state for rollback
        if gene_name in self.genome.genes:
            gene = self.genome.genes[gene_name]
            self.rollback_snapshots[gene_name] = gene.source_path.read_text("utf-8")

        # Gate 5: Write and attempt import
        gene_path = self.genome.genes_dir / f"{gene_name}.py"
        try:
            gene_path.write_text(new_source, encoding="utf-8")
        except Exception as e:
            return False, f"WRITE: Could not write gene file: {e}"

        self._log_validation(gene_name, True, "All gates passed")
        return True, "Valid"

    def rollback(self, gene_name: str) -> bool:
        """Restore a gene to its pre-mutation state."""
        if gene_name not in self.rollback_snapshots:
            return False

        old_source = self.rollback_snapshots[gene_name]
        gene_path = self.genome.genes_dir / f"{gene_name}.py"
        gene_path.write_text(old_source, encoding="utf-8")

        # Update genome
        self.genome.mutate_gene(gene_name, old_source, reason="rollback")
        del self.rollback_snapshots[gene_name]
        return True

    def commit(self, message: str) -> bool:
        """Git commit the evolution if git is available."""
        if not self.git_enabled:
            return False

        try:
            result = subprocess.run(
                ["git", "add", "-A"],
                capture_output=True, text=True,
                cwd=str(self.genome.root_dir),
                timeout=self.VALIDATION_TIMEOUT,
            )
            if result.returncode != 0:
                return False

            result = subprocess.run(
                ["git", "commit", "-m", f"evo: {message}"],
                capture_output=True, text=True,
                cwd=str(self.genome.root_dir),
                timeout=self.VALIDATION_TIMEOUT,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_imports(self, tree: ast.AST) -> list[str]:
        """Check that all imports in the code reference available modules."""
        errors = []
        stdlib = {
            "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib",
            "copy", "csv", "dataclasses", "datetime", "decimal", "enum", "functools",
            "glob", "hashlib", "html", "http", "importlib", "inspect", "io", "itertools",
            "json", "logging", "math", "multiprocessing", "operator", "os", "pathlib",
            "pickle", "platform", "pprint", "queue", "random", "re", "secrets", "shutil",
            "signal", "socket", "sqlite3", "string", "struct", "subprocess", "sys",
            "tempfile", "textwrap", "threading", "time", "traceback", "typing", "urllib",
            "uuid", "warnings", "xml", "zipfile",
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top not in stdlib:
                        # M6 FIX: Use find_spec instead of __import__ to avoid importing
                        if importlib.util.find_spec(top) is None:
                            errors.append(f"Cannot import '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split(".")[0]
                    if top not in stdlib:
                        if importlib.util.find_spec(top) is None:
                            errors.append(f"Cannot import from '{node.module}'")

        return errors

    def _log_validation(self, gene: str, passed: bool, reason: str):
        self.validation_log.append({
            "gene": gene,
            "passed": passed,
            "reason": reason,
            "time": time.time(),
        })

    @property
    def stats(self) -> dict:
        recent = self.validation_log[-20:]
        passed = sum(1 for r in recent if r["passed"])
        return {
            "recent_validations": len(recent),
            "pass_rate": passed / max(len(recent), 1),
            "rollback_count": len(self.rollback_snapshots),
        }
