"""Goal decomposition — the agent plans its own objectives and drives gene priorities.

Goals now directly influence the evolution loop by:
1. Mapping goals to target genes
2. Adjusting gene mutation priorities based on active goals
3. Completing goals when relevant genes improve
4. Evolving goals based on feedback from the memory lattice
"""

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class GoalStatus(Enum):
    PENDING, ACTIVE, COMPLETED, FAILED, EVOLVED = range(5)


@dataclass
class Goal:
    id: str
    description: str
    priority: float = 0.5
    parent_id: str | None = None
    status: GoalStatus = GoalStatus.PENDING
    sub_goals: list["Goal"] = field(default_factory=list)
    target_genes: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


class GoalDecomposer:
    """Decomposes high-level missions into actionable gene-level priorities.

    Goals → Gene priority mapping:
    - Each goal has target_genes that should be mutated to achieve it
    - Gene priorities are boosted when they serve active goals
    - When a gene serving a goal improves, the goal advances
    - Stagnant goals evolve into new sub-goals or get re-prioritized
    """

    def __init__(self, persona, memory_lattice, genome=None):
        self.persona = persona
        self.memory = memory_lattice
        self.genome = genome
        self.active_goals: list[Goal] = []
        self._counter = 0

    def set_mission(self, mission: str) -> Goal:
        """Decompose a high-level mission into actionable sub-goals with gene targets."""
        root = Goal(
            id=self._next_id(),
            description=mission,
            priority=1.0,
            status=GoalStatus.ACTIVE,
            keywords=self._extract_keywords(mission),
        )

        # Map mission keywords to likely target genes
        root.target_genes = self._map_to_genes(root.keywords)

        # Generate context-aware sub-goals
        sub_goal_templates = [
            ("Research: {}", 0.9, ["internet", "api", "data"]),
            ("Implement: {}", 0.8, ["core", "pipeline", "algorithm"]),
            ("Validate: {}", 0.7, ["test", "verify", "check"]),
            ("Optimize: {}", 0.6, ["perf", "speed", "memory"]),
        ]

        for template, priority, keywords in sub_goal_templates:
            desc = template.format(mission[:60])
            sg = Goal(
                id=self._next_id(),
                description=desc,
                priority=priority,
                parent_id=root.id,
                target_genes=self._map_to_genes(keywords + root.keywords),
                keywords=keywords + root.keywords,
            )
            root.sub_goals.append(sg)

        self.active_goals.append(root)
        # Store in memory for persistence
        if self.memory:
            try:
                from ..memory.lattice import MemoryEntry
                self.memory.store(MemoryEntry(
                    layer=3,
                    key=f"goal_{root.id}",
                    content=f"Mission: {mission}",
                    tags=["goal", "mission"],
                ))
            except Exception:
                pass
        return root

    def get_gene_priority_boost(self, gene_name: str) -> float:
        """How much should this gene's mutation priority be boosted?

        Returns 0.0-1.0 boost factor based on active goals that target this gene.
        """
        boost = 0.0
        for goal in self.active_goals:
            if goal.status != GoalStatus.ACTIVE:
                continue
            for sg in goal.sub_goals:
                if sg.status != GoalStatus.PENDING:
                    continue
                if gene_name in sg.target_genes:
                    boost += sg.priority * 0.3
        return min(1.0, boost)

    def on_gene_improved(self, gene_name: str, impact: float):
        """Notify goals when a target gene improves."""
        for goal in self.active_goals:
            for sg in goal.sub_goals:
                if gene_name in sg.target_genes and sg.status == GoalStatus.PENDING:
                    sg.attempts += 1
                    if sg.attempts >= 3 or impact > 0.3:
                        sg.status = GoalStatus.COMPLETED
                        sg.completed_at = time.time()

            # Check if all sub-goals done
            if all(sg.status == GoalStatus.COMPLETED for sg in goal.sub_goals):
                goal.status = GoalStatus.COMPLETED
                goal.completed_at = time.time()

    def evolve_stagnant_goals(self, cycle_count: int):
        """Goals that haven't progressed in a long time evolve or split."""
        now = time.time()
        for goal in list(self.active_goals):
            if goal.status != GoalStatus.ACTIVE:
                continue

            # Stagnant for too long? Evolve into new sub-goals
            stuck = [sg for sg in goal.sub_goals
                    if sg.status == GoalStatus.PENDING and sg.attempts >= 5]
            for sg in stuck:
                # Split into finer-grained goals
                new_kw = sg.keywords + ["detail", "specific", "refined"]
                sg.sub_goals = [
                    Goal(id=self._next_id(),
                         description=f"{sg.description} — Part {i+1}",
                         priority=sg.priority * 0.8,
                         parent_id=sg.id,
                         target_genes=self._map_to_genes(new_kw),
                         keywords=new_kw)
                    for i in range(2)
                ]
                sg.status = GoalStatus.EVOLVED

    def get_next_action(self) -> Goal | None:
        """Get the highest-priority pending goal with available gene targets."""
        best, best_priority = None, -1
        for g in self.active_goals:
            if g.status != GoalStatus.ACTIVE:
                continue
            for sg in g.sub_goals:
                if sg.status == GoalStatus.PENDING and sg.priority > best_priority:
                    best, best_priority = sg, sg.priority
        return best

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract domain-relevant keywords from mission text."""
        domain_keywords = {
            "trading": ["market", "strategy", "signal", "entry", "exit", "risk",
                       "position", "order", "price", "volume", "indicator"],
            "coding": ["function", "class", "module", "test", "optimize",
                      "algorithm", "pipeline", "async", "import"],
            "research": ["analyze", "search", "query", "data", "pattern",
                        "model", "experiment", "hypothesis"],
            "general": ["improve", "fix", "add", "create", "modify", "evolve",
                       "learn", "adapt"],
        }
        words = set(re.findall(r'\w+', text.lower()))
        found = []
        for domain, kwds in domain_keywords.items():
            found.extend(k for k in kwds if k in words)
        return list(set(found)) or ["general"]

    def _map_to_genes(self, keywords: list[str]) -> list[str]:
        """Map keywords to existing gene names in the genome."""
        if not self.genome or not self.genome.genes:
            return []
        matches = []
        for kw in keywords:
            for gene_name in self.genome.genes:
                if kw in gene_name.lower() and gene_name not in matches:
                    matches.append(gene_name)
        if not matches and self.genome.genes:
            # Fallback: return non-protected genes
            protected = {"mutator", "genome", "inspector", "solidify"}
            return [n for n in self.genome.genes if n not in protected][:3]
        return matches[:5]

    def _next_id(self) -> str:
        self._counter += 1
        return f"g{self._counter}"

    @property
    def stats(self) -> dict:
        total_sub = sum(len(g.sub_goals) for g in self.active_goals)
        completed = sum(
            1 for g in self.active_goals
            for sg in g.sub_goals if sg.status == GoalStatus.COMPLETED
        )
        return {
            "missions": len(self.active_goals),
            "sub_goals": total_sub,
            "completed": completed,
            "pending": total_sub - completed,
            "next_action": self.get_next_action().description[:80] if self.get_next_action() else "none",
        }
