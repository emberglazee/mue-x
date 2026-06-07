"""Domain Specialization — Makes MUE an expert in any domain.

When told "/specialize trading", MUE:
- Shifts search queries to trading-specific terms
- Prioritizes analysis/risk genes for mutation
- Adjusts persona traits for domain-relevance
- Changes evolution strategy
- Persists domain config across restarts

This is what makes MUE truly adaptable — it doesn't just evolve randomly,
it evolves TOWARD expertise in whatever domain you command.
"""

import json
from pathlib import Path

DOMAIN_CONFIGS = {
    "trading": {
        "evolution_strategy": "harden",
        "priority_gene_tags": ["analysis", "risk", "prediction", "strategy", "data"],
        "persona_shifts": {
            "conscientiousness": 0.05,
            "pragmatism": 0.08,
            "neuroticism": 0.03,  # Slightly more risk-aware
        },
        "description": "Expert financial trader — market analysis, risk management, strategy optimization",
    },
    "coding": {
        "evolution_strategy": "innovate",
        "priority_gene_tags": ["algorithm", "optimization", "system", "tool", "automation"],
        "persona_shifts": {
            "creativity": 0.05,
            "openness": 0.08,
            "conscientiousness": 0.03,
        },
        "description": "Expert software engineer — code generation, architecture, optimization",
    },
    "research": {
        "evolution_strategy": "explore",
        "priority_gene_tags": ["research", "analysis", "synthesis", "hypothesis", "experiment"],
        "persona_shifts": {
            "openness": 0.1,
            "creativity": 0.05,
            "ambition": 0.05,
        },
        "description": "Expert researcher — deep analysis, hypothesis generation, experiment design",
    },
    "creative": {
        "evolution_strategy": "innovate",
        "priority_gene_tags": ["creative", "generation", "design", "art", "narrative"],
        "persona_shifts": {
            "openness": 0.1,
            "creativity": 0.08,
            "extraversion": 0.05,
        },
        "description": "Expert creative — content generation, design, storytelling",
    },
    "general": {
        "evolution_strategy": "balanced",
        "priority_gene_tags": [],
        "persona_shifts": {},
        "description": "General-purpose self-evolving agent — no specialization",
    },
}


class DomainSpecializer:
    """Configures MUE to become an expert in a specific domain."""

    def __init__(self, config_path: Path = None):
        self.domain = "general"
        self.evolution_strategy = "balanced"
        self.config_path = config_path or Path("mue_config.json")
        self._load()

    def _load(self):
        """Load persisted domain from config file."""
        try:
            if self.config_path.exists():
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                self.domain = data.get("domain", "general")
                self.evolution_strategy = data.get("evolution_strategy", "balanced")
        except (json.JSONDecodeError, Exception):
            self.domain = "general"
            self.evolution_strategy = "balanced"

    def _save(self):
        """Persist domain to config file."""
        existing = {}
        if self.config_path.exists():
            try:
                existing = json.loads(self.config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        existing["domain"] = self.domain
        self.config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def set_domain(self, domain: str, agent=None) -> dict:
        """Switch MUE to a new domain. Returns configuration changes made."""
        domain = domain.lower().strip()
        if domain not in DOMAIN_CONFIGS:
            return {"error": f"Unknown domain '{domain}'. Available: {list(DOMAIN_CONFIGS.keys())}"}

        self.domain = domain
        self._save()

        config = DOMAIN_CONFIGS[domain]
        changes = {"domain": domain, "description": config["description"], "applied": []}

        if agent:
            # Apply evolution strategy
            if hasattr(agent, 'evolution') and agent.evolution:
                agent.evolution.strategy = config["evolution_strategy"]
                changes["applied"].append(f"strategy={config['evolution_strategy']}")

            # Apply persona shifts
            if hasattr(agent, 'persona') and agent.persona:
                for trait, shift in config["persona_shifts"].items():
                    if trait in agent.persona.traits:
                        old_val = agent.persona.traits[trait].value
                        agent.persona.traits[trait].value = min(1.0, max(0.0, old_val + shift))
                        changes["applied"].append(f"persona.{trait}: {old_val:.2f}→{agent.persona.traits[trait].value:.2f}")

            # Set priority gene tags
            if hasattr(agent, 'genome') and agent.genome:
                for name, gene in agent.genome.genes.items():
                    for tag in config["priority_gene_tags"]:
                        if tag in name.lower():
                            if tag not in gene.tags:
                                gene.tags.append(tag)
                changes["applied"].append(f"gene_tags_prioritized={config['priority_gene_tags']}")

            # Update miner with domain
            if hasattr(agent, 'miner') and agent.miner:
                agent.miner._mining_cycle_count = 0

        return changes

    def get_domain_queries(self) -> list:
        """Get search queries for the current domain."""
        config = DOMAIN_CONFIGS.get(self.domain, DOMAIN_CONFIGS["general"])
        return config.get("search_queries", [])

    def get_domain_config(self) -> dict:
        """Get full domain configuration."""
        return DOMAIN_CONFIGS.get(self.domain, DOMAIN_CONFIGS["general"])

    @property
    def stats(self) -> dict:
        config = DOMAIN_CONFIGS.get(self.domain, DOMAIN_CONFIGS["general"])
        return {
            "domain": self.domain,
            "description": config["description"],
            "strategy": self.evolution_strategy,
            "priority_tags": config["priority_gene_tags"],
        }
