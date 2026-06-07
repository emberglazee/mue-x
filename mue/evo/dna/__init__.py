"""DNA Core - Self-modifying genetic code for EVO-AGENT.

The agent's source code IS its DNA. Genes are executable code modules.
Capsules are battle-tested patterns. Mutations rewrite the agent in real-time.
"""

from .genome import Genome, Gene, Capsule, KERNEL_FILES, KernelIntegrityError
from .mutator import Mutator, PROTECTED_FILES
from .inspector import Inspector
from .sandbox import GeneSandbox, SandboxResult

__all__ = ["Genome", "Gene", "Capsule", "Mutator", "Inspector",
           "KERNEL_FILES", "KernelIntegrityError", "PROTECTED_FILES",
           "GeneSandbox", "SandboxResult"]
