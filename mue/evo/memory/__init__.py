"""Memory Lattice — 6-layer persistent memory with hybrid retrieval.

L0: Meta Rules    — Core behavioral constraints, immutable without evolution
L1: Insight Index — Minimal routing layer, maps signals → memory addresses
L2: Global Facts  — Stable long-term knowledge
L3: Task Skills   — Reusable SOPs and crystallized workflows
L4: Session Archive — Distilled task records
L5: Episodic Raw  — Raw experience traces with reinforcement signals

Hybrid search: SQLite FTS5 (keyword) + cosine similarity (semantic via embeddings).
"""

from .lattice import MemoryLattice
from .episodic import EpisodicMemory
from .retrieval import HybridRetriever

__all__ = ["MemoryLattice", "EpisodicMemory", "HybridRetriever"]
