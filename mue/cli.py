"""MUE-X Standalone CLI — No Claude Code required.

Usage:
    python -m mue              # Interactive REPL
    python -m mue status       # Agent state snapshot
    python -m mue evolve       # Force one evolution cycle
    python -m mue mine "query" # GitHub absorption
    python -m mue reflect      # Self-reflection
    python -m mue serve        # Start API server
"""

import sys
import json
import argparse
from pathlib import Path


def get_agent():
    from mue.evo.core import MueAgent
    work_dir = Path(__file__).resolve().parent
    return MueAgent(str(work_dir))


def cmd_status():
    agent = get_agent()
    state = agent.state
    print(json.dumps(state, indent=2, default=str))


def cmd_evolve():
    agent = get_agent()
    result = agent.chat("/mue evolve")
    print(result.get("response", "Evolution complete"))


def cmd_mine(query: str, domain: str = "general", file_types=None):
    agent = get_agent()
    if query.startswith("repo:"):
        repo_name = query[5:].strip()
        absorbed = agent.miner.mine_repo(repo_name, domain=domain, file_types=file_types)
    else:
        absorbed = agent.miner.mine(query, domain=domain, file_types=file_types)
    if absorbed:
        print(f"Absorbed {len(absorbed)} patterns:")
        for p in sorted(absorbed, key=lambda x: -x.value_assessment)[:10]:
            print(f"  v={p.value_assessment:.2f} [{p.pattern_type}] {p.source_repo} — {p.description[:60]}")
        print(f"Total atouts: {agent.miner.stats['total_atouts']}")
    else:
        print("No new patterns absorbed.")


def cmd_reflect():
    agent = get_agent()
    result = agent._handle_reflect_command()
    print(result.get("response", "Reflection complete"))


def cmd_serve(host: str = "127.0.0.1", port: int = 8791):
    try:
        import uvicorn
    except ImportError:
        print("uvicorn is required for API mode.")
        print("Install with: pip install fastapi uvicorn")
        sys.exit(1)
    try:
        from mue.api import create_app
        app = create_app()
    except ImportError as e:
        print(f"FastAPI is required for API mode: {e}")
        print("Install with: pip install fastapi uvicorn")
        sys.exit(1)
    print(f" MUE-X API: http://{host}:{port}")
    print(f" Docs: http://{host}:{port}/api/docs")
    uvicorn.run(app, host=host, port=port, reload=False)


def cmd_interactive():
    agent = get_agent()
    print(" MUE-X Standalone CLI")
    print(" Type /help for commands, /quit to exit")
    print()

    while True:
        try:
            msg = input("mue> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nQuitting. State preserved.")
            break

        if not msg:
            continue
        if msg in ("/quit", "/exit", "/q"):
            print("Quitting. State preserved.")
            break
        if msg == "/help":
            print("Commands: /status, /evolve, /mine <q> or repo:<name>, /reflect, /genes, /atouts, /quit")
            print("  /mine repo:user/repo --domain coding --types .rs,.go  — direct repo mining")
            continue
        if msg == "/status":
            cmd_status()
            continue
        if msg == "/evolve":
            cmd_evolve()
            continue
        if msg.startswith("/mine"):
            parts = msg[6:].strip().split(" --")
            query = parts[0].strip()
            domain = "general"
            file_types = None
            for p in parts[1:]:
                if p.startswith("domain "):
                    domain = p[7:].strip()
                if p.startswith("types "):
                    file_types = [t.strip() for t in p[6:].strip().split(",")]
            cmd_mine(query, domain=domain, file_types=file_types)
            continue
        if msg == "/reflect":
            cmd_reflect()
            continue
        if msg == "/genes":
            agent = get_agent()
            for name, gene in list(agent.genome.genes.items())[:30]:
                print(f"  {name} — fitness: {gene.fitness:.2f}")
            total = len(agent.genome.genes)
            if total > 30:
                print(f"  ... and {total - 30} more")
            continue
        if msg == "/atouts":
            agent = get_agent()
            for a in agent.miner.list_atouts():
                print(f"  {a.get('description', '?')[:70]} — {a.get('source', '?')} [v={a.get('value', 0):.2f}]")
            print(f"  Total: {agent.miner.stats['total_atouts']} atouts, avg value: {agent.miner.stats['avg_value']:.2f}")
            continue

        result = agent.chat(msg)
        print(result.get("response", "(no response)"))


def main():
    parser = argparse.ArgumentParser(description="MUE-X Self-Evolving Agent")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show agent state")
    sub.add_parser("evolve", help="Force evolution cycle")
    sub.add_parser("reflect", help="Self-reflection")
    sub.add_parser("serve", help="Start API server")
    mine_p = sub.add_parser("mine", help="GitHub absorption")
    mine_p.add_argument("query", nargs="?", default="AI agent patterns")
    mine_p.add_argument("--domain", default="general", help="Keyword scoring domain")
    mine_p.add_argument("--types", nargs="*", default=None, help="File extensions (e.g. .rs .go)")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "evolve":
        cmd_evolve()
    elif args.command == "mine":
        cmd_mine(args.query, domain=args.domain, file_types=args.types)
    elif args.command == "reflect":
        cmd_reflect()
    elif args.command == "serve":
        cmd_serve()
    else:
        cmd_interactive()


if __name__ == "__main__":
    main()
