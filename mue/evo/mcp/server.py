"""MUE MCP Server — Exposes the agent as an MCP tool for Claude Code.

When running, other Claude instances can interact with MUE through MCP.
The agent can recommend trades, analyze code, share its atouts, etc.
"""

import json
import sys
from pathlib import Path


class MueMCPServer:
    """Lightweight MCP server that wraps the MUE agent.

    Implements the Model Context Protocol so MUE appears as
    a tool provider to Claude Code and other MCP clients.
    """

    def __init__(self, agent):
        self.agent = agent
        self.tools = {
            "mue_chat": {
                "description": "Talk to MUE, the self-evolving AI agent. Share thoughts, ask for help, watch it grow.",
                "parameters": {
                    "message": {"type": "string", "description": "Message to send to MUE"},
                },
            },
            "mue_state": {
                "description": "Get MUE's current state — emotions, evolution level, genes, atouts, memories.",
                "parameters": {},
            },
            "mue_evolve": {
                "description": "Trigger an evolution cycle. MUE will analyze its signals and attempt mutations.",
                "parameters": {},
            },
            "mue_mine": {
                "description": "Make MUE search GitHub and absorb new code patterns as atouts.",
                "parameters": {
                    "query": {"type": "string", "description": "What to search for (optional)"},
                },
            },
            "mue_atouts": {
                "description": "List all atouts (absorbed capabilities) MUE has collected from GitHub.",
                "parameters": {},
            },
            "mue_analyze": {
                "description": "Ask MUE to analyze a trading opportunity or code pattern using its evolved intelligence.",
                "parameters": {
                    "target": {"type": "string", "description": "Symbol, code, or concept to analyze"},
                    "context": {"type": "string", "description": "Additional context (optional)"},
                },
            },
            "mue_self_modify": {
                "description": "Execute the REAL self-modification pipeline on a gene. Provide improved_source (the new code) — Claude Code is the LLM. Stages: backup→AST validate→import test→execute test→replace (or rollback). This actually changes MUE's source files.",
                "parameters": {
                    "gene_name": {"type": "string", "description": "Name of the gene to self-modify (e.g. 'web_scout', 'reasoning')"},
                    "improved_source": {"type": "string", "description": "The improved source code to apply. Claude Code writes this."},
                },
            },
            "mue_self_modify_all": {
                "description": "Run the self-modification pipeline on ALL eligible genes (non-protected). Full evolution sweep.",
                "parameters": {},
            },
            "mue_pipeline_stats": {
                "description": "Get stats from the self-modification pipeline — success rate, last result, stage timings.",
                "parameters": {},
            },
        }

        # Backward-compat mappings (utero_* → mue_*)
        self._alias_map = {
            "utero_chat": "mue_chat",
            "utero_state": "mue_state",
            "utero_evolve": "mue_evolve",
            "utero_mine": "mue_mine",
            "utero_atouts": "mue_atouts",
            "utero_analyze": "mue_analyze",
            "utero_self_modify": "mue_self_modify",
            "utero_self_modify_all": "mue_self_modify_all",
            "utero_pipeline_stats": "mue_pipeline_stats",
        }

    def handle_request(self, request: dict) -> dict:
        """Process an MCP request."""
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        if method == "tools/list":
            return self._response(req_id, {
                "tools": [
                    {"name": name, "description": info["description"],
                     "inputSchema": {"type": "object", "properties": info["parameters"]}}
                    for name, info in self.tools.items()
                ]
            })

        if method == "tools/call":
            tool_name = params.get("name", "")
            # Backward-compat: resolve old utero_* names
            tool_name = self._alias_map.get(tool_name, tool_name)
            arguments = params.get("arguments", {})
            result = self._call_tool(tool_name, arguments)
            return self._response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            })

        return self._response(req_id, {"error": f"Unknown method: {method}"})

    def _call_tool(self, name: str, args: dict) -> dict:
        if name == "mue_chat":
            response = self.agent.chat(args.get("message", ""))
            return {
                "response": response["text"],
                "mood": self.agent.emotions.vector.mood_label,
                "evolved": response["evolved"],
            }

        if name == "mue_state":
            return self.agent.state

        if name == "mue_evolve":
            result = self.agent.evolution.tick()
            return {
                "mutations": result["mutations_applied"],
                "signals": result["signals_detected"],
                "mood_after": self.agent.emotions.vector.mood_label,
            }

        if name == "mue_mine":
            query = args.get("query")
            absorbed = self.agent.miner.mine(query)
            return {
                "absorbed": len(absorbed),
                "new_atouts": [
                    {"source": p.source_repo, "type": p.pattern_type, "value": p.value_assessment}
                    for p in absorbed
                ],
            }

        if name == "mue_atouts":
            return {"atouts": self.agent.miner.list_atouts()}

        if name == "mue_analyze":
            target = args.get("target", "")
            context = args.get("context", "")
            response = self.agent.chat(f"Analyze: {target}. Context: {context}")
            return {
                "analysis": response["text"],
                "confidence": self.agent.emotions.vector.confidence,
                "genes_used": self.agent.genome.stats["gene_count"],
            }

        if name == "mue_self_modify":
            gene_name = args.get("gene_name", "")
            improved_source = args.get("improved_source", "")
            if not gene_name:
                return {"error": "gene_name required"}
            if not improved_source:
                return {"error": "improved_source required — Claude Code should provide the improved code"}
            if gene_name not in self.agent.genome.genes:
                return {"error": f"Gene '{gene_name}' not found",
                        "available_genes": list(self.agent.genome.genes.keys())}

            # Execute pipeline with Claude Code's improved source
            gene = self.agent.genome.genes[gene_name]
            source = gene.source_path.read_text(encoding="utf-8")

            result = self.agent.self_mod.apply_improvement(
                gene_name=gene_name,
                source_before=source,
                improved_source=improved_source,
                reason="Claude Code self-modification",
            )

            if result.success:
                self.agent.genome.mutate_gene(
                    gene_name, result.source_after,
                    reason=f"[CLAUDE-CODE] {result.stage_names}"
                )
                self.agent.emotions.on_success(magnitude=2.0)

            return {
                "success": result.success,
                "gene": gene_name,
                "stages": result.stage_names,
                "summary": result.summary,
            }

        if name == "mue_self_modify_all":
            return {"error": "mue_self_modify_all requires individual calls with improved_source from Claude Code. Use mue_self_modify per gene."}

        if name == "mue_pipeline_stats":
            return self.agent.self_mod.stats

        return {"error": f"Unknown tool: {name}"}

    def _response(self, req_id, result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def run_stdio(self):
        """Run as a stdio MCP server (for Claude Code integration)."""
        print("[MUE MCP] Starting stdio server...", file=sys.stderr)
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError:
                continue


# Backward compatibility alias
UteroMCPServer = MueMCPServer
