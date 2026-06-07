"""CuriosityEngine — Directed exploration of knowledge gaps.

"When I don't know what gene X does in case Y, I create a test."
"When I'm uncertain about a pattern, I run an experiment."

This engine generates targeted tests and experiments to fill
knowledge gaps, rather than relying on random exploration.
"""

import random
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class KnowledgeGap:
    """Something the agent doesn't know but wants to find out."""
    gap_id: str
    question: str
    target_gene: str = ""
    hypothesis: str = ""
    test_code: str = ""
    resolved: bool = False
    answer: str = ""
    created_at: float = field(default_factory=time.time)


class CuriosityEngine:
    """Generates targeted experiments to resolve uncertainty.

    When the agent encounters uncertainty — a gene with unknown behavior,
    a pattern that might work, a strategy with unclear results — it
    creates a KnowledgeGap and generates a test to fill it.

    This replaces random exploration with hypothesis-driven investigation.
    """

    def __init__(self, genome=None, memory=None, tasks_dir: Path = None):
        self.genome = genome
        self.memory = memory
        self.tasks_dir = tasks_dir or Path("tasks")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.gaps: list[KnowledgeGap] = []
        self.resolved_gaps: list[KnowledgeGap] = []
        self._counter = 0

    def detect_gaps(self) -> list[KnowledgeGap]:
        """Scan for knowledge gaps across the genome.

        Returns new gaps that were detected.
        """
        new_gaps = []

        if not self.genome:
            return new_gaps

        for name, gene in self.genome.genes.items():
            if name in ("mutator", "genome", "inspector", "solidify"):
                continue

            # Gap 1: Untested genes (low fitness, never used)
            if gene.fitness < 0.3 and gene.mutation_count == 0:
                new_gaps.append(KnowledgeGap(
                    gap_id=self._next_id(),
                    question=f"What does gene '{name}' actually do?",
                    target_gene=name,
                    hypothesis=f"Gene '{name}' is uninitialized — needs a test to discover behavior",
                ))

            # Gap 2: Frequently mutated but low fitness genes
            if gene.mutation_count > 5 and gene.fitness < 0.4:
                new_gaps.append(KnowledgeGap(
                    gap_id=self._next_id(),
                    question=f"Why does gene '{name}' stay weak despite {gene.mutation_count} mutations?",
                    target_gene=name,
                    hypothesis="Mutations may be harmful — need regression test to detect degradation",
                ))

            # Gap 3: Genes with no exploration patterns
            if gene.mutation_count > 0 and gene.fitness > 0.5:
                source = ""
                try:
                    source = gene.source_path.read_text(encoding="utf-8")
                except Exception:
                    pass
                if source and "raise" not in source and "try:" not in source:
                    new_gaps.append(KnowledgeGap(
                        gap_id=self._next_id(),
                        question=f"How does gene '{name}' handle errors?",
                        target_gene=name,
                        hypothesis="Gene may fail silently — needs error injection test",
                    ))

        # Avoid duplicate gaps
        existing_questions = {g.question for g in self.gaps}
        truly_new = [g for g in new_gaps if g.question not in existing_questions]

        self.gaps.extend(truly_new)
        return truly_new

    def generate_test(self, gap: KnowledgeGap) -> str:
        """Generate test code to resolve a knowledge gap.

        Returns executable Python test code.
        """
        if not self.genome or gap.target_gene not in self.genome.genes:
            return ""

        gene = self.genome.genes[gap.target_gene]
        test_name = gap.target_gene.replace("-", "_")

        # Generate a test that imports the gene and exercises its functions
        source = ""
        try:
            source = gene.source_path.read_text(encoding="utf-8")
        except Exception:
            return ""

        # Extract function names
        functions = []
        for line in source.split("\n"):
            stripped = line.strip()
            if stripped.startswith("def ") and not stripped.startswith("def _"):
                func_name = stripped.split("(")[0].replace("def ", "")
                if func_name not in ("__init__", "__repr__", "__str__"):
                    functions.append(func_name)

        if not functions:
            return ""

        # Generate test file
        imports = f"from mue.genes.{test_name} import {', '.join(functions[:5])}" if functions else ""
        tests = []
        for func in functions[:3]:
            tests.append(f"""
def test_{func}_exists():
    assert callable({func}), f"{func} should be callable"

def test_{func}_no_crash():
    try:
        result = {func}()
        assert result is not None, f"{func}() returned None"
    except TypeError:
        pass  # Function expects args — that's OK for now
    except Exception as e:
        assert False, f"{func}() crashed: {{e}}"
""")

        gap.test_code = f'''"""{gap.question}

Hypothesis: {gap.hypothesis}
Auto-generated by CuriosityEngine.
"""
import sys
sys.path.insert(0, ".")

{imports}

{"".join(tests)}

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
'''
        return gap.test_code

    def resolve_gap(self, gap_id: str, answer: str, test_passed: bool = False):
        """Mark a knowledge gap as resolved."""
        for gap in self.gaps:
            if gap.gap_id == gap_id:
                gap.resolved = True
                gap.answer = answer
                self.resolved_gaps.append(gap)
                self.gaps.remove(gap)
                if self.memory:
                    try:
                        from ..memory.lattice import MemoryEntry
                        self.memory.store(MemoryEntry(
                            layer=2,
                            key=f"curiosity_{gap_id}",
                            content=f"Q: {gap.question}\nA: {answer}",
                            tags=["curiosity", "resolved", "test_passed" if test_passed else "test_failed"],
                            weight=0.8 if test_passed else 0.4,
                        ))
                    except Exception:
                        pass
                return

    def get_pending_gaps(self, limit: int = 5) -> list[KnowledgeGap]:
        """Get unresolved knowledge gaps, prioritized by age."""
        return sorted(
            [g for g in self.gaps if not g.resolved],
            key=lambda g: g.created_at,
        )[:limit]

    def _next_id(self) -> str:
        self._counter += 1
        return f"gap{self._counter}"

    @property
    def stats(self) -> dict:
        return {
            "total_gaps_detected": self._counter,
            "active_gaps": len(self.gaps),
            "resolved_gaps": len(self.resolved_gaps),
            "pending": [g.question[:80] for g in self.get_pending_gaps(3)],
        }
