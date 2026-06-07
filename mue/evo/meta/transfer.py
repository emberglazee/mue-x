"""KnowledgeTransfer — Cross-domain pattern migration.

When the agent masters a pattern in one gene, it checks if that
pattern could benefit other genes. This is "learning transfer" —
the agent recognizing that what worked for gene X might work for gene Y.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TransferPattern:
    """A successful pattern that could be applied elsewhere."""
    pattern_id: str
    name: str
    description: str
    source_gene: str
    pattern_code: str  # The actual code snippet that worked
    category: str  # "optimization", "error_handling", "abstraction", etc.
    success_metric: float  # How much it improved the source gene
    transferred_to: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class TransferResult:
    """Result of attempting to apply a pattern to a target gene."""
    pattern_id: str
    target_gene: str
    success: bool
    impact: float = 0.0
    message: str = ""
    timestamp: float = field(default_factory=time.time)


class KnowledgeTransfer:
    """Detects reusable patterns and migrates them across genes.

    When a mutation significantly improves a gene, the agent extracts
    the pattern and checks if other genes could benefit from the same
    transformation. This turns single-gene wins into multi-gene improvements.
    """

    CATEGORIES = [
        "optimization",
        "error_handling",
        "abstraction",
        "performance",
        "robustness",
        "readability",
        "testing",
    ]

    def __init__(self, genome=None, memory=None):
        self.genome = genome
        self.memory = memory
        self.patterns: list[TransferPattern] = []
        self.results: list[TransferResult] = []
        self._counter = 0

    def extract_pattern(self, gene_name: str, before_source: str,
                        after_source: str, fitness_delta: float) -> TransferPattern | None:
        """Extract a reusable pattern from a successful mutation.

        Compares before/after source to identify what changed and whether
        the change is a transferable pattern.
        """
        if fitness_delta < 0.1:
            return None

        # Diff-based pattern extraction
        before_lines = before_source.split("\n")
        after_lines = after_source.split("\n")

        # Detect category from the diff
        category = self._classify_diff(before_lines, after_lines)
        if not category:
            return None

        # Extract the changed snippet (simplified: take the modified region)
        pattern_code = self._extract_diff_snippet(before_lines, after_lines)

        pattern = TransferPattern(
            pattern_id=self._next_id(),
            name=f"{category}_{gene_name}",
            description=f"{category} pattern from gene '{gene_name}'",
            source_gene=gene_name,
            pattern_code=pattern_code,
            category=category,
            success_metric=fitness_delta,
        )

        self.patterns.append(pattern)
        return pattern

    def find_candidates(self, pattern: TransferPattern) -> list[str]:
        """Find genes that could benefit from a pattern.

        Returns list of gene names that are good candidates for transfer.
        """
        if not self.genome:
            return []

        candidates = []
        source = pattern.source_gene

        for name, gene in self.genome.genes.items():
            if name == source:
                continue
            if name in pattern.transferred_to:
                continue
            if name in ("mutator", "genome", "inspector", "solidify"):
                continue

            # Check if gene has similar structure to source
            source_text = ""
            try:
                source_text = self.genome.genes[source].source_path.read_text(
                    encoding="utf-8")
            except Exception:
                pass

            target_text = ""
            try:
                target_text = gene.source_path.read_text(encoding="utf-8")
            except Exception:
                pass

            if not source_text or not target_text:
                continue

            # Structural similarity check
            if self._has_similar_structure(source_text, target_text):
                candidates.append(name)

        return candidates

    def apply_pattern(self, pattern: TransferPattern,
                      target_gene: str) -> TransferResult:
        """Attempt to apply a pattern to a target gene.

        Returns a TransferResult indicating success/failure.
        """
        if not self.genome or target_gene not in self.genome.genes:
            return TransferResult(
                pattern_id=pattern.pattern_id,
                target_gene=target_gene,
                success=False,
                message=f"Gene '{target_gene}' not found in genome",
            )

        gene = self.genome.genes[target_gene]

        try:
            source = gene.source_path.read_text(encoding="utf-8")
        except Exception as e:
            return TransferResult(
                pattern_id=pattern.pattern_id,
                target_gene=target_gene,
                success=False,
                message=f"Cannot read gene: {e}",
            )

        # Apply the pattern based on category
        modified = self._apply_by_category(pattern, source)

        if modified == source:
            return TransferResult(
                pattern_id=pattern.pattern_id,
                target_gene=target_gene,
                success=False,
                message="Pattern already present or not applicable",
            )

        # Write the modified source
        try:
            gene.source_path.write_text(modified, encoding="utf-8")
        except Exception as e:
            return TransferResult(
                pattern_id=pattern.pattern_id,
                target_gene=target_gene,
                success=False,
                message=f"Cannot write gene: {e}",
            )

        gene.mutation_count += 1
        pattern.transferred_to.append(target_gene)

        result = TransferResult(
            pattern_id=pattern.pattern_id,
            target_gene=target_gene,
            success=True,
            impact=pattern.success_metric * 0.7,  # Slightly less than original
            message=f"Applied {pattern.category} pattern from '{pattern.source_gene}'",
        )

        self.results.append(result)

        # Store in memory
        if self.memory:
            try:
                from ..memory.lattice import MemoryEntry
                self.memory.store(MemoryEntry(
                    layer=2,
                    key=f"transfer_{pattern.pattern_id}_{target_gene}",
                    content=f"Transferred {pattern.category} pattern "
                            f"from {pattern.source_gene} to {target_gene}: "
                            f"{pattern.description}",
                    tags=["transfer", pattern.category, "success"],
                    weight=0.6,
                ))
            except Exception:
                pass

        return result

    def auto_transfer(self, recent_mutations: list[dict]) -> list[TransferResult]:
        """Auto-detect and transfer patterns from recent successful mutations.

        Args:
            recent_mutations: list of dicts with keys:
                gene, before_source, after_source, fitness_delta

        Returns:
            list of TransferResult for all applied transfers
        """
        all_results = []

        for mut in recent_mutations:
            if mut.get("fitness_delta", 0) < 0.1:
                continue

            pattern = self.extract_pattern(
                mut["gene"],
                mut.get("before_source", ""),
                mut.get("after_source", ""),
                mut.get("fitness_delta", 0),
            )

            if not pattern:
                continue

            candidates = self.find_candidates(pattern)
            for candidate in candidates[:3]:  # Max 3 transfers per pattern
                result = self.apply_pattern(pattern, candidate)
                all_results.append(result)

        return all_results

    def _classify_diff(self, before: list[str], after: list[str]) -> str | None:
        """Classify the type of change between two source versions."""
        before_text = "\n".join(before)
        after_text = "\n".join(after)

        # Try/except blocks added
        if "try:" in after_text and "try:" not in before_text:
            return "error_handling"

        # Type annotations added
        if ":" in after_text and ":" not in before_text:
            if "def " in after_text:
                return "robustness"

        # List comprehensions added
        if "[" in after_text and "for " in after_text:
            if "[" not in before_text or "for " not in before_text:
                return "optimization"

        # Logging added
        if "log" in after_text.lower() and "log" not in before_text.lower():
            return "robustness"

        # Significant reduction → optimization
        if len(after) < len(before) * 0.8:
            return "optimization"

        # Significant expansion → abstraction
        if len(after) > len(before) * 1.3:
            return "abstraction"

        return "optimization"  # Default

    def _extract_diff_snippet(self, before: list[str],
                              after: list[str]) -> str:
        """Extract the relevant changed code snippet."""
        # Simple: return lines that are in 'after' but not in 'before'
        before_set = set(before)
        new_lines = [l for l in after if l not in before_set]
        if new_lines:
            return "\n".join(new_lines[:20])
        return "\n".join(after[-10:])

    def _has_similar_structure(self, source: str, target: str) -> bool:
        """Check if two source files have similar structure."""
        source_funcs = [l for l in source.split("\n")
                       if l.strip().startswith("def ")]
        target_funcs = [l for l in target.split("\n")
                       if l.strip().startswith("def ")]

        if not source_funcs or not target_funcs:
            return False

        # Similar function count
        if abs(len(source_funcs) - len(target_funcs)) <= 3:
            return True

        # Similar imports
        source_imports = [l for l in source.split("\n")
                         if l.strip().startswith("import ")
                         or l.strip().startswith("from ")]
        target_imports = [l for l in target.split("\n")
                         if l.strip().startswith("import ")
                         or l.strip().startswith("from ")]

        common = set(source_imports) & set(target_imports)
        return len(common) >= 2

    def _apply_by_category(self, pattern: TransferPattern,
                           source: str) -> str:
        """Apply a pattern to source code based on its category."""
        lines = source.split("\n")

        if pattern.category == "error_handling":
            # Add try/except around the first function body
            return self._add_error_handling(lines, pattern.pattern_code)

        elif pattern.category == "robustness":
            # Add type hints or logging
            return self._add_robustness(lines, pattern.pattern_code)

        elif pattern.category == "optimization":
            # Try to apply the optimization snippet
            return self._apply_optimization(lines, pattern.pattern_code)

        return source

    def _add_error_handling(self, lines: list[str],
                            _pattern: str) -> str:
        """Wrap first function body in try/except if not already."""
        result = []
        in_func = False
        func_indent = 0
        added = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("def ") and not added:
                in_func = True
                func_indent = len(line) - len(stripped)
                result.append(line)
                continue

            if in_func and not added:
                if stripped.startswith('"""') or stripped.startswith('#'):
                    result.append(line)
                    continue
                if stripped == "":
                    result.append(line)
                    continue
                if stripped.startswith("try:"):
                    result.append(line)
                    added = True
                    continue

                indent = " " * (func_indent + 4)
                result.append(f"{indent}try:")
                result.append(line)
                result.append(f"{indent}except Exception as e:")
                result.append(f"{indent}    import logging")
                result.append(f"{indent}    logging.error(f\"Error: {{e}}\")")
                result.append(f"{indent}    raise")
                added = True
                continue

            result.append(line)

        return "\n".join(result)

    def _add_robustness(self, lines: list[str], _pattern: str) -> str:
        """Add robustness improvements."""
        result = []
        added_logging = False

        for line in lines:
            result.append(line)
            if not added_logging and line.strip().startswith("import"):
                # Don't insert after existing imports
                pass

        if "import logging" not in "\n".join(result):
            result.insert(0, "import logging")

        return "\n".join(result)

    def _apply_optimization(self, lines: list[str],
                            pattern: str) -> str:
        """Try to apply an optimization pattern."""
        # Simple: if pattern is a comprehension, try to find a loop to replace
        if "[" in pattern and "for " in pattern and "in " in pattern:
            source = "\n".join(lines)
            # Look for simple for-append patterns
            import re
            # Pattern: for x in y: result.append(x)
            loop_pattern = re.compile(
                r'(\w+)\s*=\s*\[\]\s*\n\s*for\s+(\w+)\s+in\s+(.+?):\s*\n\s*\1\.append\((.+?)\)'
            )
            match = loop_pattern.search(source)
            if match:
                var, item, iterable, expr = match.groups()
                replacement = f"{var} = [{expr} for {item} in {iterable}]"
                return loop_pattern.sub(replacement, source, count=1)

        return "\n".join(lines)

    def _next_id(self) -> str:
        self._counter += 1
        return f"kt{self._counter}"

    @property
    def stats(self) -> dict:
        return {
            "patterns_detected": len(self.patterns),
            "transfers_attempted": len(self.results),
            "transfers_succeeded": sum(1 for r in self.results if r.success),
            "total_impact": round(sum(r.impact for r in self.results), 2),
            "categories": {
                cat: sum(1 for p in self.patterns if p.category == cat)
                for cat in self.CATEGORIES
            },
        }
