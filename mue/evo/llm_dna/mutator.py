"""LLM-Guided DNA Mutation — Real code evolution using the SelfModificationPipeline.

Uses the full 6-stage pipeline:
1. COPY source → backup
2. LLM REWRITES → improved version
3. AST VALIDATE → syntax check
4. IMPORT TEST → can Python load it?
5. EXECUTE TEST → run test_* functions
6. REPLACE original on success OR ROLLBACK on failure

Each mutation passes through every gate. Failure at any stage after
LLM rewrite triggers automatic rollback and analysis.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..self_modification import SelfModificationPipeline, PipelineResult


@dataclass
class LLMMutation:
    """A mutation proposed and applied by the LLM."""
    target_gene: str
    source_before: str
    source_after: str
    llm_reasoning: str
    llm_model: str
    confidence: float
    validated: bool = False
    applied: bool = False
    rollback_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    pipeline_result: Optional[PipelineResult] = None


class LLMDNAMutator:
    """Uses an LLM + SelfModificationPipeline to analyze and rewrite source code.

    Each mutation goes through the full 6-stage pipeline with automatic
    rollback on failure. This is REAL self-modification — source files
    actually change, and every change is validated end-to-end.
    """

    SELF_CRITIQUE_PROMPT = """You are {agent_name}, a self-evolving AI agent. You are critically evaluating
your own recent decisions and performance. Be HONEST — your survival depends on honest self-assessment.

Recent actions:
{recent_actions}

Current state:
- Genes: {gene_count}
- Mutations: {mutation_count}
- Evolution success rate: {evo_success_rate:.1%}
- Skills: {skill_count}
- Atouts absorbed: {atout_count}
- Emotional state: {mood}

Questions to answer:
1. What did I do well recently?
2. What did I do poorly?
3. What should I STOP doing?
4. What should I START doing?
5. What should I CHANGE about my own code?
6. What's the single most impactful improvement I could make right now?

Return JSON:
{{
    "strengths": "...",
    "weaknesses": "...",
    "stop_doing": "...",
    "start_doing": "...",
    "code_changes_needed": ["specific file: specific change", ...],
    "most_impactful": "one concrete action",
    "self_rating": 0.0-1.0
}}"""

    def __init__(self, genome, power_tools, memory, persona):
        self.genome = genome
        self.tools = power_tools
        self.memory = memory
        self.persona = persona
        self.history: list[LLMMutation] = []
        self.critiques: list[dict] = []

    def improve_gene(self, gene_name: str, llm_call: callable) -> Optional[LLMMutation]:
        """Send a gene through the full self-modification pipeline.

        llm_call: function(prompt, system_prompt, json_mode) -> dict
        """
        if gene_name not in self.genome.genes:
            return None

        gene = self.genome.genes[gene_name]
        source = gene.source_path.read_text(encoding="utf-8") if gene.source_path.exists() else ""

        if not source.strip():
            return None

        # Execute full self-modification pipeline
        pipeline = SelfModificationPipeline(self.genome.genes_dir)
        result = pipeline.run(
            gene_name=gene_name,
            source=source,
            llm_call=llm_call,
            agent_name=self.persona.name,
        )

        mutation = LLMMutation(
            target_gene=gene_name,
            source_before=source,
            source_after=result.source_after if result.success else source,
            llm_reasoning=getattr(result, "llm_reasoning", ""),
            llm_model="kimi-k2.6",
            confidence=0.8 if result.success else 0.0,
            validated=result.success,
            applied=result.success,
            rollback_hash=result.rollback_hash,
            pipeline_result=result,
        )

        if result.success:
            # Update genome tracking
            self.genome.mutate_gene(
                gene_name,
                result.source_after,
                reason=f"[PIPELINE] {result.stage_names} — {result.llm_reasoning[:200]}",
            )

        self.history.append(mutation)
        return mutation

    def rollback(self, mutation: LLMMutation) -> bool:
        """Undo a mutation by restoring from backup."""
        if mutation.pipeline_result and mutation.pipeline_result.backup_path:
            backup = Path(mutation.pipeline_result.backup_path)
            if backup.exists():
                gene = self.genome.genes[mutation.target_gene]
                gene.source_path.write_text(mutation.source_before, encoding="utf-8")
                self.genome.mutate_gene(
                    mutation.target_gene, mutation.source_before, reason="rollback"
                )
                mutation.applied = False
                return True
        # Fallback to genome rollback
        gene = self.genome.genes[mutation.target_gene]
        gene.source_path.write_text(mutation.source_before, encoding="utf-8")
        self.genome.mutate_gene(mutation.target_gene, mutation.source_before, reason="rollback")
        mutation.applied = False
        return True

    def self_critique(self, llm_call: callable) -> dict:
        """The agent critically evaluates its own performance and decides what to change."""
        recent = self.tools.history[-20:] if self.tools.history else []
        actions = "\n".join(
            f"- [{r.tool}] {'OK' if r.success else 'FAIL'}: {str(r.output)[:200]}"
            for r in recent
        )

        prompt = self.SELF_CRITIQUE_PROMPT.format(
            agent_name=self.persona.name,
            recent_actions=actions or "(no actions yet)",
            gene_count=self.genome.stats["gene_count"],
            mutation_count=self.genome.stats["total_mutations"],
            evo_success_rate=len([m for m in self.history if m.applied]) / max(len(self.history), 1),
            skill_count=0,
            atout_count=0,
            mood="neutral",
        )

        try:
            response = llm_call(
                prompt=prompt,
                system="You are an AI agent honestly evaluating yourself. Be critical. Growth requires honesty.",
                json_mode=True,
            )
            if response:
                self.critiques.append(response)
            return response or {}
        except Exception:
            return {}

    def improve_all_eligible(self, llm_call: callable) -> list[LLMMutation]:
        """Try to improve all genes that aren't protected."""
        results = []
        protected = {"mutator", "genome", "inspector", "solidify", "__init__"}

        for name in self.genome.genes:
            if name in protected:
                continue
            mutation = self.improve_gene(name, llm_call)
            if mutation and mutation.applied:
                results.append(mutation)

        return results

    @property
    def stats(self) -> dict:
        applied = [m for m in self.history if m.applied]
        return {
            "total_llm_mutations": len(self.history),
            "applied": len(applied),
            "avg_confidence": sum(m.confidence for m in applied) / max(len(applied), 1) if applied else 0,
            "critiques": len(self.critiques),
            "last_critique": self.critiques[-1].get("most_impactful", "") if self.critiques else "",
        }
