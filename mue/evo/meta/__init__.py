"""Meta-Cognition — Layer 3 of the self-evolving agent.

This is the "brain watching the brain" — MUE's ability to reason about
its OWN functioning, diagnose problems, and adapt its own behavior.

Capabilities:
- SelfDiagnosis: detect anomalies, corruption, degradation
- CuriosityEngine: generate targeted tests for unknowns
- ResourceMonitor: track CPU, RAM, disk, mutation budget
- CycleAdapter: auto-tune the evolution loop timing/strategy
- KnowledgeTransfer: cross-domain pattern migration
"""

from .diagnosis import SelfDiagnosis
from .curiosity import CuriosityEngine
from .resources import ResourceMonitor
from .cycle_adapter import CycleAdapter
from .transfer import KnowledgeTransfer

__all__ = [
    "SelfDiagnosis",
    "CuriosityEngine",
    "ResourceMonitor",
    "CycleAdapter",
    "KnowledgeTransfer",
]
