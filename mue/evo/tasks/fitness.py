"""FitnessUpdater — Updates gene fitness based on REAL task outcomes.

This is the bridge from Layer 2 back to Layer 1. Task results flow
through the mapper and into gene fitness values that the evolution
loop uses for selection.

Key principle: gene fitness is no longer based on mutation count or
arbitrary increments. It's grounded in actual task performance.
"""

import time
from collections import defaultdict

from .mapper import GeneTaskMapper


class FitnessUpdater:
    """Updates gene fitness based on measured task outcomes.

    Three fitness components:
    1. Task success rate — how often tasks involving this gene succeed
    2. Average task score — the quality of outcomes
    3. Usage frequency — genes used more often for successful tasks get a bonus

    The fitness decays over time if a gene stops being used (use it or lose it).
    """

    DECAY_RATE = 0.01  # Per cycle without use
    MIN_FITNESS = 0.05
    DEATH_THRESHOLD = 0.1  # Genes below this for DEATH_WINDOW cycles are purged
    DEATH_WINDOW = 10

    def __init__(self, genome, mapper: GeneTaskMapper):
        self.genome = genome
        self.mapper = mapper
        self.fitness_history: dict[str, list[float]] = defaultdict(list)
        self.cycles_without_use: dict[str, int] = defaultdict(int)
        self.total_updates = 0
        self.last_update = time.time()

    def update_all(self):
        """Update all gene fitness values from task outcomes."""
        if not self.genome or not self.genome.genes:
            return

        self.total_updates += 1
        updated = 0

        for gene_name in self.genome.genes:
            if gene_name in ("mutator", "genome", "inspector", "solidify"):
                continue

            task_fitness = self.mapper.get_gene_fitness_from_tasks(gene_name)
            scores = self.mapper.gene_scores.get(gene_name, [])

            if scores:
                # Real fitness from task outcomes
                gene = self.genome.genes[gene_name]
                old_fitness = gene.fitness

                # Blend: 80% task-based, 20% prior
                gene.fitness = 0.8 * task_fitness + 0.2 * old_fitness
                gene.fitness = max(self.MIN_FITNESS, min(1.0, gene.fitness))

                self.cycles_without_use[gene_name] = 0
                updated += 1
            else:
                # Decay unused genes
                self.cycles_without_use[gene_name] += 1
                if self.cycles_without_use[gene_name] > 0:
                    gene = self.genome.genes[gene_name]
                    gene.fitness = max(
                        self.MIN_FITNESS,
                        gene.fitness - self.DECAY_RATE * self.cycles_without_use[gene_name]
                    )

            self.fitness_history[gene_name].append(self.genome.genes[gene_name].fitness)
            if len(self.fitness_history[gene_name]) > 100:
                self.fitness_history[gene_name] = self.fitness_history[gene_name][-100:]

        self.last_update = time.time()
        return updated

    def get_genes_to_purge(self) -> list[str]:
        """Return genes that should be removed (below death threshold for too long).

        This is the GENE DEATH mechanism: genes that never contribute
        to successful tasks are pruned from the genome.
        """
        to_purge = []
        for gene_name, cycles in self.cycles_without_use.items():
            if gene_name in ("mutator", "genome", "inspector", "solidify"):
                continue
            if cycles >= self.DEATH_WINDOW:
                gene = self.genome.genes.get(gene_name)
                if gene and gene.fitness <= self.DEATH_THRESHOLD:
                    to_purge.append(gene_name)
        return to_purge

    def purge_dead_genes(self) -> int:
        """Remove genes that have been dead for too long. Returns count purged."""
        dead = self.get_genes_to_purge()
        purged = 0
        for gene_name in dead:
            try:
                self.genome.remove_gene(gene_name)
                purged += 1
            except Exception:
                pass
        return purged

    def get_fitness_trend(self, gene_name: str, window: int = 5) -> float:
        """Is this gene improving (+), stable (0), or degrading (-)?"""
        history = self.fitness_history.get(gene_name, [])
        if len(history) < window:
            return 0.0
        recent = history[-window:]
        return recent[-1] - recent[0]

    def get_best_genes(self, n: int = 5) -> list[tuple[str, float]]:
        """Top N genes by real task fitness."""
        scored = []
        for gene_name in self.genome.genes:
            if gene_name in ("mutator", "genome", "inspector", "solidify"):
                continue
            fitness = self.mapper.get_gene_fitness_from_tasks(gene_name)
            scored.append((gene_name, fitness))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n]

    def get_worst_genes(self, n: int = 5) -> list[tuple[str, float]]:
        """Bottom N genes by real task fitness — need improvement."""
        scored = []
        for gene_name in self.genome.genes:
            if gene_name in ("mutator", "genome", "inspector", "solidify"):
                continue
            fitness = self.mapper.get_gene_fitness_from_tasks(gene_name)
            scored.append((gene_name, fitness))
        scored.sort(key=lambda x: x[1])
        return scored[:n]

    @property
    def stats(self) -> dict:
        death_candidates = self.get_genes_to_purge()
        return {
            "total_updates": self.total_updates,
            "genes_tracked": len(self.fitness_history),
            "death_candidates": len(death_candidates),
            "death_candidate_names": death_candidates[:5],
            "best_gene": self.get_best_genes(1)[0] if self.genome and self.genome.genes else None,
            "worst_gene": self.get_worst_genes(1)[0] if self.genome and self.genome.genes else None,
            "last_update_ago": time.time() - self.last_update,
        }
