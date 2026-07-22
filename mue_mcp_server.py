"""MUE-X MCP Server — Hermes-native entry point with full MCP protocol.

Usage (stdio transport for Hermes native MCP client):
    python mue_mcp_server.py

Stdin/stdout follow JSON-RPC (MCP protocol).
All bootstrapping noise goes to stderr.
"""
import json
import os
import sys
from pathlib import Path

# Ensure the mue package is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mue"))

# Suppress stdout during bootstrap — MCP uses stdout for JSON-RPC
# Save real stdout, redirect to stderr temporarily
_real_stdout = sys.stdout
sys.stdout = sys.stderr

try:
    from evo.core import MueAgent

    work_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mue")
    config = {
        "name": "Mue",
        "evolution_strategy": "balanced",
        "domain": "general",
    }
    agent = MueAgent(work_dir=str(work_dir), config=config)
finally:
    # Restore stdout — MCP server communicates over stdout
    sys.stdout = _real_stdout


def _mcp_response(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _mcp_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_request(method: str, params: dict, req_id):
    """Process a single MCP request."""
    # ── Protocol life-cycle ──
    if method == "initialize":
        version = params.get("protocolVersion", "2024-11-05")
        return _mcp_response(req_id, {
            "protocolVersion": version,
            "capabilities": {
                "tools": {},
                "prompts": {},
                "resources": {},
                "experimental": {},
            },
            "serverInfo": {"name": "mue-x", "version": agent.VERSION},
        })

    if method == "notifications/initialized":
        return None  # No response for notifications

    if method == "notifications/cancelled":
        return None

    if method == "ping":
        return _mcp_response(req_id, {})

    # ── Tool discovery ──
    if method == "tools/list":
        tools = [
            {
                "name": "mue_chat",
                "description": "Talk to MUE, the self-evolving AI agent. Share thoughts, ask for help, watch it grow.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to send to MUE"},
                    },
                    "required": ["message"],
                },
            },
            {
                "name": "mue_state",
                "description": "Get MUE's current state — emotions, evolution level, genes, atouts, memories.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "mue_evolve",
                "description": "Trigger an evolution cycle. MUE will analyze its signals and attempt mutations.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "mue_mine",
                "description": "Make MUE search GitHub and absorb new code patterns as atouts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Text search query (optional if 'repo' is given)"},
                        "repo": {"type": "string", "description": "Specific GitHub repo to mine (e.g. 'emberglazee/Hearts-of-Modding'). Skips search, goes straight to clone + extract."},
                        "domain": {"type": "string", "description": "Domain for keyword scoring/filtering: 'general', 'coding', 'trading', 'research', etc. Default: 'general'"},
                        "file_types": {"type": "array", "items": {"type": "string"}, "description": "File extensions to mine, e.g. ['.py', '.rs']. Default: ['.py']"},
                    },
                },
            },
            {
                "name": "mue_atouts",
                "description": "List all atouts (absorbed capabilities) MUE has collected from GitHub.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "mue_analyze",
                "description": "Ask MUE to analyze a trading opportunity or code pattern using its evolved intelligence.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Symbol, code, or concept to analyze"},
                        "context": {"type": "string", "description": "Additional context (optional)"},
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "mue_self_modify",
                "description": "Execute the REAL self-modification pipeline on a gene. Provide improved_source — Claude Code is the LLM.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "gene_name": {"type": "string", "description": "Name of the gene to self-modify (e.g. 'web_scout')"},
                        "improved_source": {"type": "string", "description": "The improved source code to apply"},
                    },
                    "required": ["gene_name", "improved_source"],
                },
            },
            {
                "name": "mue_pipeline_stats",
                "description": "Get stats from the self-modification pipeline — success rate, last result, stage timings.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
        return _mcp_response(req_id, {"tools": tools})

    # ── Tool execution ──
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        result_text = _call_tool(name, args)
        return _mcp_response(req_id, {
            "content": [{"type": "text", "text": json.dumps(result_text, indent=2)}],
        })

    return _mcp_error(req_id, -32601, f"Unknown method: {method}")


def _call_tool(name: str, args: dict) -> dict:
    """Execute a MUE-X tool and return a JSON-serializable result."""
    if name == "mue_chat":
        response = agent.chat(args.get("message", ""))
        return {
            "response": response.get("text", ""),
            "mood": agent.emotions.vector.mood_label,
            "evolved": response.get("evolved", False),
        }

    if name == "mue_state":
        return agent.state

    if name == "mue_evolve":
        result = agent.evolution.tick()
        return {
            "mutations": result.get("mutations_applied", 0),
            "signals": result.get("signals_detected", 0),
            "mood_after": agent.emotions.vector.mood_label,
        }

    if name == "mue_mine":
        query = args.get("query")
        repo = args.get("repo")
        domain = args.get("domain", "general")
        file_types = args.get("file_types")
        if repo:
            absorbed = agent.miner.mine_repo(repo, domain=domain, file_types=file_types)
        else:
            absorbed = agent.miner.mine(query, domain=domain, file_types=file_types)
        return {
            "absorbed": len(absorbed),
            "new_atouts": [
                {"source": p.source_repo, "type": p.pattern_type, "value": p.value_assessment}
                for p in absorbed
            ],
        }

    if name == "mue_atouts":
        return {"atouts": agent.miner.list_atouts()}

    if name == "mue_analyze":
        target = args.get("target", "")
        context = args.get("context", "")
        response = agent.chat(f"Analyze: {target}. Context: {context}")
        return {
            "analysis": response.get("text", ""),
            "confidence": agent.emotions.vector.confidence,
            "genes_used": agent.genome.stats["gene_count"],
        }

    if name == "mue_self_modify":
        gene_name = args.get("gene_name", "")
        improved_source = args.get("improved_source", "")
        if not gene_name:
            return {"error": "gene_name required"}
        if not improved_source:
            return {"error": "improved_source required"}
        if gene_name not in agent.genome.genes:
            return {
                "error": f"Gene '{gene_name}' not found",
                "available_genes": list(agent.genome.genes.keys()),
            }
        gene = agent.genome.genes[gene_name]
        source = gene.source_path.read_text(encoding="utf-8")
        result = agent.self_mod.apply_improvement(
            gene_name=gene_name,
            source_before=source,
            improved_source=improved_source,
            reason="Claude Code self-modification",
        )
        if result.success:
            agent.genome.mutate_gene(
                gene_name, result.source_after,
                reason=f"[CLAUDE-CODE] {result.stage_names}",
            )
            agent.emotions.on_success(magnitude=2.0)
        return {
            "success": result.success,
            "gene": gene_name,
            "stages": result.stage_names,
            "summary": result.summary,
        }

    if name == "mue_pipeline_stats":
        return agent.self_mod.stats

    return {"error": f"Unknown tool: {name}"}


def run_stdio():
    """Run as a stdio MCP server (for Hermes native MCP client)."""
    import sys
    print("[MUE MCP] Starting stdio server...", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = None
        try:
            request = json.loads(line)
            method = request.get("method", "")
            params = request.get("params", {})
            req_id = request.get("id")

            response = handle_request(method, params, req_id)
            if response is not None:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            continue
        except Exception as exc:
            rid = None
            if request is not None:
                rid = request.get("id")
            print(json.dumps(_mcp_error(rid, -32603, str(exc))), flush=True)


# ── Main ──
if __name__ == "__main__":
    run_stdio()
