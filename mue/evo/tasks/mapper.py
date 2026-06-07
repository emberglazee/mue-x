"""GeneTaskMapper — Associates genes with the tasks they impact.

When a task runs, which genes contributed to its outcome? This mapper
tracks the relationship so gene fitness can be grounded in real results.
"""

import time
from collections import defaultdict

from .definition import TaskDefinition, TaskResult


class GeneTaskMapper:
    """Maps genes to tasks and tracks their contribution history.

    Three mapping strategies:
    1. Explicit: task.genes_involved is set directly
    2. Auto: scan gene source for function/class names mentioned in task description
    3. Learned: over time, observe which genes correlate with task success
    """

    def __init__(self, genome=None):
        self.genome = genome
        self.gene_tasks: dict[str, list[str]] = defaultdict(list)  # gene -> task_ids
        self.task_genes: dict[str, list[str]] = defaultdict(list)  # task_id -> genes
        self.gene_scores: dict[str, list[float]] = defaultdict(list)  # gene -> recent scores
        self._access_counts: dict[str, int] = defaultdict(int)

    def map_task(self, task: TaskDefinition):
        """Register the gene ↔ task relationship."""
        if task.genes_involved:
            self._add_explicit(task)
        else:
            self._auto_map(task)

    def _add_explicit(self, task: TaskDefinition):
        for gene in task.genes_involved:
            if gene not in self.gene_tasks:
                self.gene_tasks[gene] = []
            if task.task_id not in self.gene_tasks[gene]:
                self.gene_tasks[gene].append(task.task_id)
            if gene not in self.task_genes[task.task_id]:
                self.task_genes[task.task_id].append(gene)

    def _auto_map(self, task: TaskDefinition):
        """Heuristically map task to genes by keyword matching."""
        if not self.genome or not self.genome.genes:
            return
        desc_lower = (task.name + " " + task.description).lower()
        for gene_name in self.genome.genes:
            if gene_name in ("mutator", "genome", "inspector", "solidify"):
                continue
            # Match gene name or function names in source
            if gene_name.lower() in desc_lower:
                self.gene_tasks[gene_name].append(task.task_id)
                self.task_genes[task.task_id].append(gene_name)
                continue
            # Check source for matching function names
            try:
                source = self.genome.genes[gene_name].source_path.read_text(encoding="utf-8")
                for line in source.split("\n"):
                    if line.strip().startswith("def "):
                        func_name = line.strip().split("(")[0].replace("def ", "")
                        if func_name.lower().replace("_", " ") in desc_lower:
                            self.gene_tasks[gene_name].append(task.task_id)
                            self.task_genes[task.task_id].append(gene_name)
                            break
            except Exception:
                pass

    def record_result(self, task: TaskDefinition, result: TaskResult):
        """Record a task result against its contributing genes."""
        genes = self.task_genes.get(task.task_id, task.genes_involved)
        for gene in genes:
            self.gene_scores[gene].append(result.score)
            if len(self.gene_scores[gene]) > 50:
                self.gene_scores[gene] = self.gene_scores[gene][-50:]
            self._access_counts[gene] += 1

    def get_gene_fitness_from_tasks(self, gene_name: str) -> float:
        """Compute gene fitness from actual task outcomes.

        This is the REAL fitness — derived from task results, not
        random increments from AST mutations.
        """
        scores = self.gene_scores.get(gene_name, [])
        if not scores:
            return 0.5  # Unknown

        # Weighted: recent scores matter more
        if len(scores) <= 2:
            return sum(scores) / len(scores)

        weighted = 0.0
        total_weight = 0.0
        for i, s in enumerate(scores):
            w = 1.0 + (i / len(scores))  # Later scores have higher weight
            weighted += s * w
            total_weight += w
        return weighted / total_weight if total_weight > 0 else 0.5

    def get_genes_for_task_type(self, task_description: str) -> list[str]:
        """Find genes that have historically succeeded on similar tasks."""
        desc_lower = task_description.lower()
        candidates = []
        for gene, task_ids in self.gene_tasks.items():
            score = self.get_gene_fitness_from_tasks(gene)
            if score > 0.5:
                candidates.append((gene, score))
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [g for g, _ in candidates[:5]]

    @property
    def stats(self) -> dict:
        return {
            "genes_mapped": len(self.gene_tasks),
            "total_accesses": sum(self._access_counts.values()),
            "avg_gene_score": (
                sum(self.get_gene_fitness_from_tasks(g) for g in self.gene_tasks)
                / max(len(self.gene_tasks), 1)
            ),
            "most_used_genes": sorted(
                self._access_counts.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }
