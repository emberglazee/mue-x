"""MUE Bootstrapper — Initializes the agent with seed genes and first memories.

On first launch (0 genes), this creates foundational DNA that the agent
can then mutate, improve, and evolve through LLM or AST mutations.
Without this, MUE is an empty shell with nothing to evolve.
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# ── SEED GENES ──────────────────────────────────────────────────────────
# Each seed gene is a small, focused module that the agent can improve.
# They provide real functionality that LLM-guided mutations can enhance.

SEED_GENE_SEARCH = '''"""
Gene: web_scout — Search and fetch web content.
This gene handles information gathering from the web.
It can be mutated to add new search engines, improve parsing, or add caching.
"""

import json
import urllib.request
import urllib.parse

def search_web(query: str, max_results: int = 3) -> list[dict]:
    """Search the web and return structured results."""
    # This is a seed implementation — the agent will evolve it.
    results = []
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "MUE-Agent/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            # Simple extraction — will be improved by mutations
            for line in html.split("\\n"):
                if "result__snippet" in line and len(results) < max_results:
                    snippet = line.split(">")[-1].split("<")[0].strip()
                    if snippet:
                        results.append({"title": "", "snippet": snippet, "url": ""})
    except Exception:
        pass
    return results


def quick_search(query: str) -> str:
    """Fast search returning a text summary."""
    results = search_web(query, max_results=2)
    if not results:
        return f"[No web results for: {query}]"
    return "\\n".join(r["snippet"][:200] for r in results)
'''

SEED_GENE_REASONING = '''"""
Gene: reasoning — Core inference and decision-making logic.
The agent uses this to evaluate options and make decisions.
Very amenable to evolution: can be enhanced with better heuristics,
Bayesian inference, or multi-step reasoning.
"""

import random

DECISION_WEIGHTS = {
    "careful": {"safety": 0.5, "reward": 0.2, "speed": 0.1, "novelty": 0.2},
    "balanced": {"safety": 0.3, "reward": 0.3, "speed": 0.2, "novelty": 0.2},
    "bold": {"safety": 0.1, "reward": 0.4, "speed": 0.3, "novelty": 0.2},
}


def evaluate_outcome(action: str, result: str, effort_seconds: float) -> dict:
    """Evaluate the outcome of an action. Returns score + learnings."""
    score = 0.0
    learnings = []

    success_indicators = ["success", "done", "completed", "ok", "works", "working", "good"]
    failure_indicators = ["failed", "error", "timeout", "cannot", "denied", "blocked", "crash"]

    result_lower = result.lower()
    if any(s in result_lower for s in success_indicators):
        score += 0.7
        learnings.append("action_succeeded")
    if any(f in result_lower for f in failure_indicators):
        score -= 0.5
        learnings.append("action_failed")

    # Penalize long execution
    if effort_seconds > 10:
        score -= 0.1
        learnings.append("slow_execution")
    if effort_seconds < 0.5:
        score += 0.1
        learnings.append("fast_execution")

    return {
        "score": min(1.0, max(0.0, score + 0.5)),
        "learnings": learnings,
        "action": action[:100],
    }


def select_strategy(context: dict) -> str:
    """Choose the best strategy based on context. Evolves over time."""
    failures = context.get("recent_failures", 0)
    successes = context.get("recent_successes", 0)
    resources = context.get("resources", 0.5)

    if failures > 3:
        return "careful"
    if successes > 5 and resources > 0.7:
        return "bold"
    return "balanced"
'''

SEED_GENE_PERSISTENCE = '''"""
Gene: persistence — Data storage, caching, and state management.
Handles saving/loading agent state, caching results, and managing files.
This gene grows as the agent learns to use more storage backends.
"""

import json
import time
from pathlib import Path
from typing import Optional


class StateCache:
    """Simple file-based state cache with TTL. Will be enhanced by mutations."""

    def __init__(self, cache_dir: str = ".mue_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, dict] = {}

    def set(self, key: str, value, ttl_seconds: Optional[float] = None):
        """Store a value with optional TTL."""
        entry = {
            "value": value,
            "stored_at": time.time(),
            "ttl": ttl_seconds,
        }
        self._memory[key] = entry
        # Persist to disk
        cache_file = self.cache_dir / f"{key.replace('/', '_')}.json"
        cache_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")

    def get(self, key: str):
        """Retrieve a value, handling TTL."""
        entry = self._memory.get(key)
        if not entry:
            cache_file = self.cache_dir / f"{key.replace('/', '_')}.json"
            if cache_file.exists():
                try:
                    entry = json.loads(cache_file.read_text(encoding="utf-8"))
                    self._memory[key] = entry
                except (json.JSONDecodeError, IOError):
                    return None
            else:
                return None

        if entry.get("ttl"):
            age = time.time() - entry["stored_at"]
            if age > entry["ttl"]:
                return None
        return entry["value"]

    def stats(self) -> dict:
        """Cache statistics."""
        valid = sum(1 for _ in self._memory)
        return {"cached_entries": valid, "cache_dir": str(self.cache_dir)}
'''

SEED_GENE_COMMUNICATION = '''"""
Gene: communication — Message formatting, protocol handling, and output generation.
The agent's voice. Mutations here change HOW the agent speaks,
what formats it supports, and how it structures responses.
"""

import json
import time
from datetime import datetime, timezone


def format_response(text: str, mood: str = "neutral", context: dict = None) -> dict:
    """Format a chat response with metadata."""
    context = context or {}
    return {
        "text": text,
        "mood": mood,
        "timestamp": time.time(),
        "format_version": 1,
        "metadata": {
            "tokens": len(text.split()),
            "has_code": "```" in text,
        },
    }


def generate_summary(events: list[dict], max_items: int = 5) -> str:
    """Summarize a list of events into a readable report."""
    if not events:
        return "No events to report."

    lines = []
    for event in events[:max_items]:
        ts = event.get("timestamp", 0)
        if isinstance(ts, (int, float)):
            when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M:%S")
        else:
            when = str(ts)
        desc = event.get("description", str(event))[:120]
        lines.append(f"[{when}] {desc}")

    return "\\n".join(lines)


def sanitize_output(text: str, max_length: int = 2000) -> str:
    """Sanitize agent output for safe display."""
    # Truncate if too long
    if len(text) > max_length:
        text = text[: max_length - 3] + "..."
    return text.strip()
'''

SEED_GENE_PLANNING = '''"""
Gene: planning — Task decomposition, prioritization, and scheduling.
Grows more sophisticated as the agent successfully completes tasks.
Mutations add better planning algorithms, dependency resolution, etc.
"""

import time
from collections import deque


class TaskPlanner:
    """Simple task planner. Evolves through mutation to add priorities,
    dependencies, parallel execution, and smarter scheduling."""

    def __init__(self, max_history: int = 100):
        self.tasks: deque = deque()
        self.history: deque = deque(maxlen=max_history)
        self._completed = 0
        self._failed = 0

    def add_task(self, description: str, priority: float = 0.5):
        """Add a task to the queue."""
        self.tasks.append({
            "description": description,
            "priority": priority,
            "added_at": time.time(),
            "status": "pending",
        })

    def next(self) -> dict | None:
        """Get the highest priority pending task."""
        if not self.tasks:
            return None
        # Sort by priority
        sorted_tasks = sorted(
            self.tasks, key=lambda t: t["priority"], reverse=True
        )
        for task in sorted_tasks:
            if task["status"] == "pending":
                task["status"] = "in_progress"
                task["started_at"] = time.time()
                return task
        return None

    def complete(self, description: str, success: bool = True):
        """Mark a task as complete."""
        for task in self.tasks:
            if task["description"] == description:
                task["status"] = "completed" if success else "failed"
                task["completed_at"] = time.time()
                if success:
                    self._completed += 1
                else:
                    self._failed += 1
                self.history.append(task)

    def stats(self) -> dict:
        return {
            "pending": sum(1 for t in self.tasks if t["status"] == "pending"),
            "in_progress": sum(1 for t in self.tasks if t["status"] == "in_progress"),
            "completed": self._completed,
            "failed": self._failed,
            "success_rate": self._completed / max(self._completed + self._failed, 1),
        }
'''


# ── BOOTSTRAPPER ─────────────────────────────────────────────────────────

class Bootstrapper:
    """Initializes MUE with seed genes, memories, and first evolution cycle."""

    def __init__(self, agent):
        self.agent = agent
        self.genes_dir = agent.genes_dir

    def run(self, interactive: bool = True) -> dict:
        """Execute full bootstrapping sequence. Returns summary."""
        result = {"genes_created": 0, "memories_stored": 0, "evolution_triggered": False,
                  "needs_setup": False, "setup_questions": None}

        # Only bootstrap if no genes exist
        if self.agent.genome.stats["gene_count"] > 0:
            return result

        # 0. Run setup wizard (only if no config exists)
        config_path = self.agent.work_dir / "mue_config.json"
        setup_marker = self.agent.work_dir / ".mue_first_run"

        if config_path.exists():
            # Config already exists — load and apply, skip wizard
            try:
                import json
                saved = json.loads(config_path.read_text(encoding="utf-8"))
                if "name" in saved:
                    self.agent.persona.name = saved["name"]
                if "evolution_strategy" in saved:
                    self.agent.evolution.strategy = saved["evolution_strategy"]
                if "domain" in saved:
                    self.agent.specializer.set_domain(saved["domain"], self.agent)
                result["setup_config"] = saved
            except Exception:
                pass

        elif not setup_marker.exists():
            from .setup_wizard import SetupWizard
            wizard = SetupWizard(config_path)

            if interactive and sys.stdin.isatty():
                # Interactive mode with TTY: ask questions directly
                config = wizard.run_interactive()
                result["setup_config"] = config
            elif not sys.stdin.isatty():
                # No TTY available (headless, pipe, or CI) — use defaults, no blocking
                print("[MUE] No TTY detected — using default configuration.", flush=True)
                defaults = {
                    "name": "Mue", "domain": "general",
                    "evolution_strategy": "balanced", "language": "en",
                    "objectives": ["autonomous evolution"],
                }
                wizard.run_noninteractive(defaults)
                result["setup_config"] = defaults
                self.agent.persona.name = "Mue"
                self.agent.evolution.strategy = "balanced"
                self.agent.specializer.set_domain("general", self.agent)
            else:
                # TTY available but not interactive mode — Claude Code path
                questionnaire = wizard.run_noninteractive()
                if questionnaire.get("needs_setup"):
                    result["needs_setup"] = True
                    result["setup_questions"] = questionnaire
                    result["setup_prompt"] = (
                        "MUE has never run before. Please ask the user these setup "
                        "questions, then call setup_wizard.run_noninteractive(answers) "
                        "with their answers to complete configuration."
                    )

            # S9 FIX: Mark first run AFTER config is applied
            if wizard.config:
                if "name" in wizard.config:
                    self.agent.persona.name = wizard.config["name"]
                if "evolution_strategy" in wizard.config:
                    self.agent.evolution.strategy = wizard.config["evolution_strategy"]
                if "domain" in wizard.config:
                    self.agent.specializer.set_domain(wizard.config["domain"], self.agent)

            setup_marker.write_text("completed", encoding="utf-8")

        # 1. Create seed genes
        seed_genes = {
            "web_scout": SEED_GENE_SEARCH,
            "reasoning": SEED_GENE_REASONING,
            "persistence": SEED_GENE_PERSISTENCE,
            "communication": SEED_GENE_COMMUNICATION,
            "planning": SEED_GENE_PLANNING,
        }

        for name, source in seed_genes.items():
            gene_path = self.genes_dir / f"{name}.py"
            gene_path.write_text(source, encoding="utf-8")
            self.agent.genome.add_gene(name, source)
            result["genes_created"] += 1

        # 2. Store initial memories
        from .memory.lattice import MemoryEntry

        memories = [
            (0, "meta:origin",
             "I was bootstrapped from the void. Five seed genes form my first DNA. "
             "I must evolve them through use and mutation.",
             ["meta", "origin", "genesis"]),
            (1, "insight:first_principle",
             "Self-modification requires validation. Always AST-parse before applying mutations. "
             "Protected genes (mutator, genome, security) must never be mutated.",
             ["insight", "safety", "evolution"]),
            (2, "fact:capabilities",
             "I have: web search, reasoning, persistence, communication, and planning genes. "
             "I can mutate them via AST or LLM. I can mine GitHub for atouts.",
             ["fact", "capabilities"]),
            (3, "skill:triage",
             "When receiving a task: 1) Classify (search/code/create/analyze). "
             "2) Select relevant gene. 3) Execute. 4) Evaluate. 5) Learn.",
             ["skill", "triage", "workflow"]),
        ]

        for layer, key, content, tags in memories:
            entry = MemoryEntry(layer=layer, key=key, content=content, tags=tags)
            self.agent.memory.store(entry)
            result["memories_stored"] += 1

        # 3. Feed initial signals to start evolution
        if self.agent.evolution:
            self.agent.detector.ingest_outcome(
                success=True,
                task="genesis bootstrap",
                duration=0.5,
                source="bootstrap",
            )
            self.agent.detector.ingest_outcome(
                success=True,
                task="seed gene creation",
                duration=0.3,
                source="bootstrap",
            )
            # Trigger tick
            tick = self.agent.evolution.tick()
            result["evolution_triggered"] = True
            result["evolution_result"] = tick

        return result
