"""TaskRunner — Executes tasks and captures real metrics.

Domain-pluggable: each domain provides its own executor via register_executor().
Default executors are provided for general, coding, and trading domains.

This is the bridge between gene mutations and REAL outcomes.
"""

import importlib
import subprocess
import time
import traceback
from typing import Any, Callable, Optional

from .definition import TaskDefinition, TaskResult, TaskSuite, Domain


class TaskRunner:
    """Executes tasks across domains and captures real performance metrics.

    Domain executors are pluggable: register a callable for any domain.
    The runner handles timeouts, retries, error capture, and result
    normalization into a standard TaskResult format.
    """

    def __init__(self):
        self._executors: dict[Domain, Callable] = {}
        self._register_defaults()
        self.results: list[TaskResult] = []
        self.total_runs = 0
        self.successful_runs = 0

    def register_executor(self, domain: Domain, executor: Callable):
        """Register a custom executor for a domain.

        executor(task: TaskDefinition) -> (output, metrics_dict)
        """
        self._executors[domain] = executor

    def run(self, task: TaskDefinition) -> TaskResult:
        """Execute a single task and return the result."""
        self.total_runs += 1
        task.run_count += 1
        task.last_run_at = time.time()

        executor = self._executors.get(task.domain, self._executors[Domain.GENERAL])
        start = time.perf_counter()

        try:
            output, metrics = executor(task)
            duration_ms = (time.perf_counter() - start) * 1000

            # Compute score using task's metric function
            if task.metric_fn:
                score = task.metric_fn(output, task.expected_output)
            else:
                score = 1.0 if output is not None else 0.0

            result = TaskResult(
                task_id=task.task_id,
                success=score >= 0.5,
                score=min(1.0, max(0.0, score)),
                duration_ms=duration_ms,
                output=output,
                metrics=metrics or {},
            )
            if result.success:
                self.successful_runs += 1

        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            result = TaskResult(
                task_id=task.task_id,
                success=False,
                score=0.0,
                duration_ms=duration_ms,
                error=f"{type(e).__name__}: {str(e)[:200]}",
                metrics={"exception": traceback.format_exc()[:500]},
            )

        self.results.append(result)
        if len(self.results) > 1000:
            self.results = self.results[-500:]

        return result

    def run_suite(self, suite: TaskSuite, max_parallel: int = 1) -> list[TaskResult]:
        """Run all ready tasks in a suite."""
        results = []
        for task in suite.get_ready_tasks():
            result = self.run(task)
            results.append(result)
            if not result.success and task.max_retries > 1:
                for _ in range(task.max_retries - 1):
                    retry = self.run(task)
                    if retry.success:
                        results[-1] = retry
                        break
        return results

    def _register_defaults(self):
        """Register built-in executors for each domain."""

        def _general_executor(task: TaskDefinition):
            """Default: import and call a function specified in input_data."""
            module_path = task.input_data.get("module")
            func_name = task.input_data.get("function", "main")
            args = task.input_data.get("args", [])
            kwargs = task.input_data.get("kwargs", {})

            if module_path:
                try:
                    spec = importlib.util.spec_from_file_location(
                        "task_module", module_path
                    )
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        func = getattr(mod, func_name)
                        output = func(*args, **kwargs)
                        return output, {"module": module_path, "function": func_name}
                except Exception:
                    pass

            # Fallback: run as standalone Python
            code = task.input_data.get("code", "")
            if code:
                namespace = {}
                exec(code, namespace)
                func = namespace.get(func_name, lambda: None)
                output = func(*args, **kwargs)
                return output, {"exec_type": "inline"}

            return None, {"exec_type": "noop"}

        def _coding_executor(task: TaskDefinition):
            """Coding domain: run tests against generated code."""
            code = task.input_data.get("code", "")
            test_code = task.input_data.get("test_code", "")
            if not test_code:
                # Default: check if code is valid Python
                try:
                    compile(code, "<task>", "exec")
                    return True, {"validation": "compiles", "lines": len(code.split("\n"))}
                except SyntaxError as e:
                    return False, {"validation": "syntax_error", "error": str(e)}

            # Run actual tests
            combined = f"{code}\n\n{test_code}"
            try:
                result = subprocess.run(
                    ["python", "-c", combined],
                    capture_output=True, text=True, timeout=task.timeout_seconds,
                )
                passed = result.returncode == 0
                return passed, {
                    "validation": "tests_passed" if passed else "tests_failed",
                    "stdout": result.stdout[:500],
                    "stderr": result.stderr[:500],
                }
            except subprocess.TimeoutExpired:
                return False, {"validation": "timeout"}

        def _trading_executor(task: TaskDefinition):
            """Trading domain: evaluate a strategy signal."""
            signal = task.input_data.get("signal", {})
            market_data = task.input_data.get("market_data", {})

            # Basic checks: signal must have direction, entry, TP, SL
            checks = []
            if signal.get("direction") in ("long", "short"):
                checks.append(True)
            else:
                checks.append(False)

            if signal.get("entry") and signal.get("tp") and signal.get("sl"):
                # Validate TP/SL make sense for direction
                if signal["direction"] == "long":
                    checks.append(signal["tp"] > signal["entry"] > signal["sl"])
                else:
                    checks.append(signal["sl"] > signal["entry"] > signal["tp"])
            else:
                checks.append(False)

            if signal.get("confidence", 0) >= 0.5:
                checks.append(True)
            else:
                checks.append(False)

            score = sum(checks) / max(len(checks), 1)
            return score >= 0.6, {
                "validation": "signal_valid" if score >= 0.6 else "signal_invalid",
                "checks_passed": sum(checks),
                "checks_total": len(checks),
                "signal_score": score,
            }

        def _research_executor(task: TaskDefinition):
            """Research domain: evaluate synthesis quality."""
            output_text = task.input_data.get("output", "")
            sources = task.input_data.get("sources", [])
            query = task.input_data.get("query", "")

            # Quality heuristics
            checks = []
            if len(output_text) > 100:  # Has substantive output
                checks.append(True)
            if len(sources) > 0:  # Has citations
                checks.append(True)
            if query and query.lower()[:20] in output_text.lower():  # Relevance
                checks.append(True)
            if "http" in output_text or "www." in output_text:  # Has references
                checks.append(True)

            score = sum(checks) / max(max(len(checks), 1), 4)
            return score >= 0.5, {
                "length": len(output_text),
                "sources_count": len(sources),
                "score": score,
            }

        self._executors = {
            Domain.GENERAL: _general_executor,
            Domain.CODING: _coding_executor,
            Domain.TRADING: _trading_executor,
            Domain.RESEARCH: _research_executor,
            Domain.CREATIVE: _general_executor,
            Domain.SECURITY: _general_executor,
            Domain.DATA_SCIENCE: _general_executor,
            Domain.DEVOPS: _general_executor,
        }

    @property
    def stats(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "success_rate": self.successful_runs / max(self.total_runs, 1),
            "recent_scores": [r.score for r in self.results[-20:]],
            "domains": list(self._executors.keys()),
        }
