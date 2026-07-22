"""MUE-X MCP Server — Hermes-native entry point.

Usage (stdio transport for Hermes native MCP client):
    python mue_mcp_server.py

Stdin/stdout follow JSON-RPC (MCP protocol).
All bootstrapping noise goes to stderr.
"""
import os
import sys

# Ensure the mue package is importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mue"))

# Suppress stdout during bootstrap — MCP uses stdout for JSON-RPC
# Save real stdout, redirect to stderr temporarily
_real_stdout = sys.stdout
sys.stdout = sys.stderr

try:
    from evo.core import MueAgent
    from evo.mcp import MueMCPServer

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

# Run MCP stdio server
server = MueMCPServer(agent)
server.run_stdio()
