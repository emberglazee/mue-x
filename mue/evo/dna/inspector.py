"""Inspector — Self-awareness module. The agent reads and understands its own code.

This is the key to recursive self-improvement: the agent can inspect any of
its genes, analyze their structure, and identify improvement opportunities.
"""

import ast
import hashlib
from pathlib import Path
from typing import Any


class Inspector:
    """Gives the agent the ability to read, understand, and critique its own code."""

    def __init__(self, genome):
        self.genome = genome
        self._ast_cache: dict[str, tuple[int, int, ast.AST]] = {}  # path -> (mtime, size, tree)

    def _parse_cached(self, source_path: Path, source: str) -> ast.AST | None:
        """Parse source with mtime+size cache. Avoids re-parsing unchanged files."""
        try:
            stat = source_path.stat()
            key = str(source_path)
            cached = self._ast_cache.get(key)
            if cached and cached[0] == int(stat.st_mtime) and cached[1] == stat.st_size:
                return cached[2]
            tree = ast.parse(source)
            self._ast_cache[key] = (int(stat.st_mtime), stat.st_size, tree)
            if len(self._ast_cache) > 200:
                # Evict oldest 50 entries
                keys = list(self._ast_cache.keys())[:50]
                for k in keys:
                    del self._ast_cache[k]
            return tree
        except SyntaxError:
            return None

    def read_gene(self, name: str) -> dict[str, Any]:
        """Deep inspection of a single gene."""
        if name not in self.genome.genes:
            return {"error": f"Gene '{name}' not found"}

        gene = self.genome.genes[name]
        source = gene.source_path.read_text("utf-8") if gene.source_path.exists() else ""

        tree = self._parse_cached(gene.source_path, source)
        if tree is None:
            return {
                "name": name,
                "hash": gene.content_hash,
                "error": "Syntax error in gene source",
                "source": source,
            }

        functions = []
        classes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "args": [a.arg for a in node.args.args],
                    "line": node.lineno,
                    "decorators": [
                        (d.id if isinstance(d, ast.Name) else str(d))
                        for d in node.decorator_list
                    ],
                    "docstring": ast.get_docstring(node),
                })
            elif isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    imports.append(alias.name)

        return {
            "name": name,
            "hash": gene.content_hash,
            "lines": len(source.splitlines()),
            "size_bytes": len(source),
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "mutations": gene.mutation_count,
            "fitness": gene.fitness,
            "complexity_estimate": _estimate_complexity(tree),
        }

    def read_all_genes(self) -> dict[str, Any]:
        """Full self-portrait of the agent's DNA."""
        genes_report = {}
        for name in self.genome.genes:
            genes_report[name] = self.read_gene(name)

        return {
            "stats": self.genome.stats,
            "genes": genes_report,
            "capsules": {
                name: {"description": c.description, "genes": c.gene_names, "success_rate": c.success_rate}
                for name, c in self.genome.capsules.items()
            },
        }

    def find_improvement_targets(self) -> list[dict]:
        """Identify genes that could benefit from mutation."""
        targets = []
        for name, gene in self.genome.genes.items():
            if name in {"mutator", "genome", "inspector"}:
                continue
            source = gene.source_path.read_text("utf-8") if gene.source_path.exists() else ""

            score = 0
            reasons = []

            # Low fitness genes
            if gene.fitness < 0.3:
                score += 3
                reasons.append("low fitness")

            # Genes with many mutations but still low fitness (local optimum)
            if gene.mutation_count > 5 and gene.fitness < 0.5:
                score += 2
                reasons.append("stuck in local optimum")

            # Genes without error handling
            if "try" not in source and "except" not in source:
                score += 1
                reasons.append("no error handling")

            # Genes with high complexity
            tree = self._parse_cached(gene.source_path, source)
            if tree is None:
                score += 4
                reasons.append("broken syntax")
            else:
                complexity = _estimate_complexity(tree)
                if complexity > 10:
                    score += 1
                    reasons.append(f"high complexity ({complexity})")

            if score >= 2:
                targets.append({
                    "name": name,
                    "urgency": score / 10.0,
                    "reasons": reasons,
                    "current_fitness": gene.fitness,
                    "mutations_so_far": gene.mutation_count,
                })

        targets.sort(key=lambda t: -t["urgency"])
        return targets

    def diff_gene(self, name: str) -> dict:
        """Show what changed in this gene across mutations."""
        if name not in self.genome.genes:
            return {"error": f"Gene '{name}' not found"}

        gene = self.genome.genes[name]
        current = gene.source_path.read_text("utf-8") if gene.source_path.exists() else ""

        return {
            "name": name,
            "current_hash": gene.content_hash,
            "parent_hash": gene.parent_hash,
            "mutation_count": gene.mutation_count,
            "last_mutated": gene.last_mutated,
            "current_source": current,
        }


def _estimate_complexity(tree: ast.AST) -> int:
    """Cyclomatic complexity estimate from AST."""
    complexity = 1
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1
    return complexity
