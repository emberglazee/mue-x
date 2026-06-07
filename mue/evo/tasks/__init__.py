"""Task Execution & Real Feedback — Layer 2 of the self-evolving agent.

This is the missing piece: without real tasks, real metrics, and real
feedback, gene fitness is random noise. This module provides:

- TaskDefinition: standard structure for evaluable tasks (domain-pluggable)
- TaskRunner: executes tasks and captures real metrics
- GeneTaskMapper: associates genes with the tasks they impact
- FitnessUpdater: updates gene fitness based on REAL task outcomes

Architecture:
    TaskDefinition → TaskRunner → TaskResult → GeneTaskMapper → FitnessUpdater
                                                                       ↓
                                                              gene.fitness (REAL)
"""

from .definition import TaskDefinition, TaskResult, TaskSuite, Domain
from .runner import TaskRunner
from .mapper import GeneTaskMapper
from .fitness import FitnessUpdater

__all__ = [
    "TaskDefinition", "TaskResult", "TaskSuite", "Domain",
    "TaskRunner", "GeneTaskMapper", "FitnessUpdater",
]
