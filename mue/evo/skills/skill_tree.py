"""Skill Tree — Dependencies and relationships between skills.

Models how skills build on each other, forming a directed acyclic graph
of capabilities that grows as the agent evolves.
"""

from collections import defaultdict
from pathlib import Path


class SkillTree:
    """DAG of skills and their dependencies."""

    def __init__(self):
        self.dependencies: dict[str, set[str]] = defaultdict(set)
        self.dependents: dict[str, set[str]] = defaultdict(set)  # Reverse edges
        self.categories: dict[str, str] = {}

    def add_skill(self, name: str, deps: list[str], category: str = "general"):
        """Register a skill with its dependencies. Detects cycles."""
        if name in self.categories:
            return  # Already registered
        self.categories[name] = category
        for dep in deps:
            # Cycle detection: if dep depends on name (transitively), skip
            if self._would_create_cycle(name, dep):
                continue
            self.dependencies[name].add(dep)
            self.dependents[dep].add(name)

    def _would_create_cycle(self, new_skill: str, new_dep: str) -> bool:
        """Check if adding new_dep -> new_skill would create a cycle."""
        if new_dep == new_skill:
            return True
        visited = set()
        stack = [new_dep]
        while stack:
            node = stack.pop()
            if node == new_skill:
                return True
            if node not in visited:
                visited.add(node)
                stack.extend(self.dependencies.get(node, set()))
        return False

    def get_required_skills(self, skill_name: str) -> set[str]:
        """Get all skills that must be loaded before this one."""
        result = set()
        stack = list(self.dependencies.get(skill_name, set()))
        while stack:
            dep = stack.pop()
            if dep not in result:
                result.add(dep)
                stack.extend(self.dependencies.get(dep, set()))
        return result

    def get_dependent_skills(self, skill_name: str) -> set[str]:
        """Get all skills that depend on this one."""
        result = set()
        stack = list(self.dependents.get(skill_name, set()))
        while stack:
            dep = stack.pop()
            if dep not in result:
                result.add(dep)
                stack.extend(self.dependents.get(dep, set()))
        return result

    def find_root_skills(self) -> list[str]:
        """Skills with no dependencies — foundational capabilities."""
        return [name for name, deps in self.dependencies.items() if not deps]

    def find_leaf_skills(self) -> list[str]:
        """Skills nothing depends on — highest-level capabilities."""
        all_skills = set(self.dependencies.keys()) | set(self.dependents.keys())
        return [s for s in all_skills if s not in self.dependents or not self.dependents[s]]

    def get_category_tree(self) -> dict[str, list[str]]:
        """Skills grouped by category."""
        result = defaultdict(list)
        for name, cat in self.categories.items():
            result[cat].append(name)
        return dict(result)

    @property
    def stats(self) -> dict:
        return {
            "total_skills": len(self.categories),
            "categories": len(set(self.categories.values())),
            "roots": self.find_root_skills(),
            "leaves": self.find_leaf_skills()[:10],
        }
