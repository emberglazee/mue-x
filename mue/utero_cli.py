"""MUE CLI — Non-blocking command interface for interacting with MUE.

Runs in a thread alongside the evolution loop so commands don't block mutations.
Commands are dispatched to the agent for immediate action.

Usage:
    python utero.py --headless          # Auto-start CLI thread
    python utero.py --headless --domain trading  # With domain specialization

Commands:
    /specialize <domain>  Become an expert in <domain>
    /status               Full agent state snapshot
    /genes                List all genes with fitness and mutations
    /mine [query]         Trigger GitHub absorption
    /evolve               Force evolution tick
    /atouts               List absorbed capabilities
    /memories             Show recent memories
    /reflect              Force self-reflection
    /config               Show configuration
    /help                 Show all commands
    /quit                 Graceful shutdown
"""

import json
import sys
import threading
import time


class UteroCLI:
    """Non-blocking CLI that reads commands in a thread."""

    COMMANDS_HELP = {
        "specialize": "/specialize <domain> — Become an expert (trading|coding|research|creative|general)",
        "status": "/status — Full agent state snapshot",
        "genes": "/genes — List all genes with fitness and mutation stats",
        "mine": "/mine [query] — Trigger GitHub absorption (with optional query)",
        "evolve": "/evolve — Force evolution tick",
        "atouts": "/atouts — List absorbed capabilities (atouts)",
        "memories": "/memories — Show recent memories",
        "reflect": "/reflect — Force self-reflection",
        "config": "/config — Show current configuration",
        "help": "/help — Show this help",
        "quit": "/quit — Graceful shutdown",
    }

    def __init__(self, agent, domain_specializer=None):
        self.agent = agent
        self.specializer = domain_specializer
        self.running = False
        self._thread = None

    def start(self):
        """Start the CLI thread."""
        self.running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        print("\n  CLI READY — Type /help for commands\n")

    def stop(self):
        """Signal the CLI to stop."""
        self.running = False

    def _read_loop(self):
        """Read stdin in a loop, dispatch commands."""
        while self.running:
            try:
                line = sys.stdin.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                cmd = line.strip()
                if not cmd:
                    continue
                self._dispatch(cmd)
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break
            except Exception as e:
                print(f"  [!] CLI error: {e}")

    def _dispatch(self, cmd: str):
        """Route a command to the right handler."""
        if not cmd.startswith("/"):
            return

        parts = cmd.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove leading /
        args = parts[1] if len(parts) > 1 else ""

        handler = getattr(self, f"_cmd_{command}", None)
        if handler:
            result = handler(args)
            if result:
                print(result)
        else:
            print(f"  [!] Unknown command: /{command}. Type /help for commands.")

    # ── COMMAND HANDLERS ──

    def _cmd_specialize(self, args: str) -> str:
        if not args:
            return f"  Usage: /specialize <domain>\n  Available: trading, coding, research, creative, general"
        if not self.specializer:
            return "  [!] Domain specializer not available"
        result = self.specializer.set_domain(args, self.agent)
        if "error" in result:
            return f"  [!] {result['error']}"
        lines = [f"  [SPECIALIZED] Domain: {result['domain']}"]
        for change in result.get("applied", []):
            lines.append(f"    → {change}")
        return "\n".join(lines)

    def _cmd_status(self, _: str) -> str:
        state = self.agent.state
        domain_info = ""
        if self.specializer:
            domain_info = f"\n  Domain: {self.specializer.domain} ({self.specializer.get_domain_config()['description']})"

        return f"""
  ═══ MUE STATE ═══{domain_info}
  Persona: {state['persona']['name']} | Stage: {state['persona']['age_stage']}
  Mood: {state['emotions']['mood_label']}
  Genes: {state['genome']['gene_count']} | Mutations: {state['genome']['total_mutations']}
  Avg Fitness: {state['genome']['avg_fitness']:.2f}
  Skills: {state['skills']['total_skills']} | Trending: {', '.join(state['skills']['trending'][:3]) or 'none'}
  Atouts: {state['atouts']['total_atouts']} | Avg Value: {state['atouts']['avg_value']:.2f}
  Memories: {state['memory']['total_memories']}
  Plugins: {state['plugins']['total_plugins']}
  Evolution: {state.get('evolution', {})}
  Security: {state['security']['writes_blocked']} blocked | {state['security']['bash_blocked']} bash blocked
  ════════════════════
"""

    def _cmd_genes(self, _: str) -> str:
        genes = self.agent.genome.genes
        if not genes:
            return "  No genes. Bootstrapping may be needed."
        lines = ["  ═══ GENES ═══"]
        for name, gene in sorted(genes.items(), key=lambda x: -x[1].fitness):
            mutations = gene.mutation_count
            fitness = gene.fitness
            tags = ", ".join(gene.tags) if gene.tags else "none"
            lines.append(f"  {name}: fitness={fitness:.2f} mutations={mutations} tags=[{tags}]")
        lines.append(f"  Total: {len(genes)} genes | Avg fitness: {self.agent.genome.stats['avg_fitness']:.2f}")
        return "\n".join(lines)

    def _cmd_mine(self, args: str) -> str:
        query = args.strip() or None
        # Do local absorption first
        local = self.agent.miner.local_absorb()
        result_parts = []
        if local:
            result_parts.append(f"  Local absorption: {len(local)} atouts from project dirs")
        # Then GitHub mining
        if query:
            absorbed = self.agent.miner.mine(query)
            if absorbed:
                result_parts.append(f"  GitHub: {len(absorbed)} atouts from search '{query}'")
        if not result_parts:
            return f"  No new atouts found. Total: {self.agent.miner.stats['total_atouts']}"
        return "\n".join(result_parts)

    def _cmd_evolve(self, _: str) -> str:
        result = self.agent.evolution.tick()
        if result["mutations_applied"] > 0:
            return f"  [EVOLVED] {result['mutations_applied']} mutations applied. Genes: {self.agent.genome.stats['gene_count']}"
        return f"  [TICK] No mutations applied. Signals: {result['signals_detected']} active, {result.get('autonomous_signals', 0)} autonomous."

    def _cmd_atouts(self, _: str) -> str:
        atouts = self.agent.miner.list_atouts()
        if not atouts:
            return "  No atouts absorbed yet. Use /mine to start absorption."
        lines = ["  ═══ ATOUTS ═══"]
        for a in atouts[:10]:
            lines.append(f"  {a['source']}: {a['description'][:80]} (value={a['value']:.2f}, success={a['success_rate']:.0%})")
        return "\n".join(lines)

    def _cmd_memories(self, _: str) -> str:
        recent = self.agent.memory.get_recent(limit=10)
        if not recent:
            return "  No memories stored."
        lines = ["  ═══ RECENT MEMORIES ═══"]
        for mem in recent:
            lines.append(f"  [{mem.layer}] {mem.key}: {mem.content[:100]}...")
        return "\n".join(lines)

    def _cmd_reflect(self, _: str) -> str:
        r = self.agent.reflection.reflect("on_demand")
        if r:
            return f"""
  ═══ SELF-REFLECTION ═══
  Rating: {r.self_rating:.0%}
  Insights: {'; '.join(r.insights[:3]) if r.insights else 'none'}
  Regrets: {'; '.join(r.regrets[:2]) if r.regrets else 'none'}
  Resolutions: {'; '.join(r.resolutions[:3]) if r.resolutions else 'none'}
  Proposed Changes: {'; '.join(r.code_changes_proposed[:2]) if r.code_changes_proposed else 'none'}
  ══════════════════════
"""
        return "  Quiet contemplation..."

    def _cmd_config(self, _: str) -> str:
        domain_info = ""
        if self.specializer:
            s = self.specializer.stats
            domain_info = f"\n  Domain: {s['domain']} — {s['description']}\n  Strategy: {s['strategy']}\n  Priority Tags: {s['priority_tags']}"
        return f"""
  ═══ CONFIG ═══{domain_info}
  Version: {getattr(self.agent, 'VERSION', 'unknown')}
  Auto-mine interval: {getattr(self.agent.miner, 'auto_mine_interval', 'N/A')} cycles
  ═══════════════
"""

    def _cmd_help(self, _: str) -> str:
        lines = ["  ═══ MUE COMMANDS ═══"]
        for name, desc in sorted(self.COMMANDS_HELP.items()):
            lines.append(f"  {desc}")
        return "\n".join(lines)

    def _cmd_quit(self, _: str) -> str:
        print("  Shutting down MUE...")
        self.stop()
        if hasattr(self.agent, 'evolution') and self.agent.evolution:
            self.agent.evolution.stop()
        if hasattr(self.agent, 'memory'):
            self.agent.memory.close()
        print("  MUE shutdown complete.")
        sys.exit(0)
