"""TaskDefinition — Standard structure for evaluable tasks.

Every domain (trading, coding, research, etc.) defines tasks using
this unified structure. The key insight: a task has an objective,
measurable success criteria, and a set of genes that contribute to it.
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class Domain(Enum):
    """The domain a task belongs to. Plug in more domains here."""
    GENERAL = "general"
    TRADING = "trading"
    CODING = "coding"
    RESEARCH = "research"
    CREATIVE = "creative"
    SECURITY = "security"
    DATA_SCIENCE = "data_science"
    DEVOPS = "devops"


@dataclass
class TaskDefinition:
    """A single evaluable task.

    This is the contract: given input, produce expected_output, measure
    success via metric_fn. Genes contributing to this task get scored
    based on how well the task performs.
    """
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    domain: Domain = Domain.GENERAL

    # Execution contract
    input_data: dict = field(default_factory=dict)
    expected_output: Any = None
    metric_fn: Optional[Callable] = None  # (output, expected) -> 0.0-1.0

    # Gene attribution
    genes_involved: list[str] = field(default_factory=list)
    gene_weights: dict[str, float] = field(default_factory=dict)

    # Constraints
    timeout_seconds: float = 30.0
    max_retries: int = 1
    tags: list[str] = field(default_factory=list)

    # Lifecycle
    created_at: float = field(default_factory=time.time)
    run_count: int = 0
    last_run_at: float = 0.0

    def with_metric(self, fn: Callable) -> "TaskDefinition":
        self.metric_fn = fn
        return self

    def with_genes(self, genes: list[str], weights: dict[str, float] = None) -> "TaskDefinition":
        self.genes_involved = genes
        self.gene_weights = weights or {g: 1.0 / len(genes) for g in genes}
        return self


@dataclass
class TaskResult:
    """The outcome of a single task execution."""
    task_id: str
    success: bool
    score: float  # 0.0-1.0, derived from metric_fn
    duration_ms: float
    output: Any = None
    error: str = ""
    metrics: dict = field(default_factory=dict)  # Domain-specific metrics
    timestamp: float = field(default_factory=time.time)

    @property
    def quality(self) -> str:
        if self.score >= 0.8:
            return "excellent"
        if self.score >= 0.6:
            return "good"
        if self.score >= 0.4:
            return "acceptable"
        if self.score >= 0.2:
            return "poor"
        return "failed"


@dataclass
class TaskSuite:
    """A collection of related tasks for a domain.

    Suites are the unit of domain-pluggability: plug in a TradingSuite,
    CodingSuite, etc. Each suite defines the tasks that exercise and
    evaluate the genes relevant to that domain.
    """
    name: str
    domain: Domain
    description: str = ""
    tasks: list[TaskDefinition] = field(default_factory=list)
    version: int = 1

    def add(self, task: TaskDefinition) -> "TaskSuite":
        task.domain = self.domain
        self.tasks.append(task)
        return self

    def get_ready_tasks(self) -> list[TaskDefinition]:
        """Tasks that are ready to run (have metric_fn and genes_involved)."""
        return [t for t in self.tasks if t.metric_fn and t.genes_involved]

    @property
    def stats(self) -> dict:
        return {
            "name": self.name,
            "domain": self.domain.value,
            "task_count": len(self.tasks),
            "ready_count": len(self.get_ready_tasks()),
            "version": self.version,
        }
