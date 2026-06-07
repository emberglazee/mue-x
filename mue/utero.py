"""MUE — The Self-Evolving AI Agent (Pure MCP).

Claude Code IS the LLM. MUE is an MCP server that Claude Code connects to.
No external API keys, no OpenRouter, no dotenv.

Usage:
    python utero.py                     # MCP server (Claude Code connects via MCP)
    python utero.py --headless          # Autonomous evolution loop (AST + autonomous signals)
    python utero.py --headless --domain trading  # Specialize in trading
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evo.core import MueAgent
from evo.mcp import UteroMCPServer
from evo.specialization import DomainSpecializer
from utero_cli import UteroCLI


def main():
    work_dir = Path(__file__).parent

    # Parse domain from CLI
    domain = "general"
    args = sys.argv[1:]
    if "--domain" in args:
        idx = args.index("--domain")
        if idx + 1 < len(args):
            domain = args[idx + 1]

    config = {
        "name": "Mue",
        "evolution_strategy": "balanced",
        "domain": domain,
    }

    agent = MueAgent(work_dir=str(work_dir), config=config)

    # Setup domain specialization
    config_path = work_dir / "mue_config.json"
    specializer = DomainSpecializer(config_path)
    if domain != "general":
        result = specializer.set_domain(domain, agent)
        if "error" not in result:
            print(f"  [DOMAIN] Specialized in: {domain}")

    cli = UteroCLI(agent, specializer)

    if "--headless" in args:
        # Headless mode: evolution loop + CLI thread
        agent.start()  # Banner + evolution loop (blocking)
        # CLI starts after banner, in parallel with loop
        cli.start()
    else:
        # MCP server mode: Claude Code connects via stdin/stdout
        mcp = UteroMCPServer(agent)
        mcp.run_stdio()


if __name__ == "__main__":
    main()
