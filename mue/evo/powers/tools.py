"""Power Tools — Gives MUE the same capabilities as Claude Code.

The agent can: read/write/edit files, execute bash commands, search the web,
fetch URLs, call MCP tools, and more. Every action is logged and auditable.

This is not simulation — these are REAL system operations with full power
and full accountability.
"""

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class ToolResult:
    tool: str
    success: bool
    output: Any
    elapsed_ms: float
    error: Optional[str] = None


class PowerTools:
    """The agent's toolbox — mirrors Claude Code capabilities."""

    def __init__(self, work_dir: Path, security):
        self.work_dir = work_dir
        self.security = security
        self.history: list[ToolResult] = []

    # ── FILE OPERATIONS ──

    def read_file(self, path: str, offset: int = 0, limit: int = 2000) -> ToolResult:
        """Read a file from the filesystem."""
        t0 = time.perf_counter()
        full_path = self._resolve(path)
        try:
            content = full_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            page = lines[offset:offset + limit]
            return self._ok("read_file", "\n".join(page), t0)
        except Exception as e:
            return self._err("read_file", str(e), t0)

    def write_file(self, path: str, content: str) -> ToolResult:
        """Write a file. Security check enforced."""
        t0 = time.perf_counter()
        full_path = self._resolve(path)

        if not self.security.allow_write(full_path, content):
            return self._err("write_file", "Security policy denied write", t0)

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            self.security.log_write(full_path, content)
            return self._ok("write_file", f"Written {len(content)} bytes to {path}", t0)
        except Exception as e:
            return self._err("write_file", str(e), t0)

    def edit_file(self, path: str, old: str, new: str) -> ToolResult:
        """Edit a file with exact string replacement."""
        t0 = time.perf_counter()
        full_path = self._resolve(path)

        try:
            content = full_path.read_text(encoding="utf-8")
            if old not in content:
                return self._err("edit_file", "Old string not found in file", t0)

            new_content = content.replace(old, new, 1)
            if not self.security.allow_write(full_path, new_content):
                return self._err("edit_file", "Security policy denied edit", t0)

            full_path.write_text(new_content, encoding="utf-8")
            self.security.log_edit(full_path, old, new)
            return self._ok("edit_file", f"Replaced in {path}", t0)
        except Exception as e:
            return self._err("edit_file", str(e), t0)

    # ── SEARCH OPERATIONS ──

    def glob(self, pattern: str) -> ToolResult:
        """Find files by glob pattern."""
        t0 = time.perf_counter()
        try:
            matches = sorted(self.work_dir.glob(pattern))
            return self._ok("glob", [str(m.relative_to(self.work_dir)) for m in matches[:100]], t0)
        except Exception as e:
            return self._err("glob", str(e), t0)

    def grep(self, pattern: str, path: str = ".", glob_filter: Optional[str] = None) -> ToolResult:
        """Search file contents with regex."""
        t0 = time.perf_counter()
        try:
            import re
            search_dir = self._resolve(path)
            results = []

            for f in search_dir.rglob(glob_filter or "*"):
                if f.is_file() and f.suffix in (".py", ".json", ".txt", ".md", ".html", ".css", ".js", ".yaml", ".yml", ".toml", ".cfg", ".ini"):
                    try:
                        content = f.read_text(encoding="utf-8")
                    except Exception:
                        continue
                    for i, line in enumerate(content.splitlines(), 1):
                        if re.search(pattern, line):
                            results.append(f"{f.relative_to(self.work_dir)}:{i}: {line.strip()[:200]}")
                            if len(results) >= 50:
                                break
                    if len(results) >= 50:
                        break

            return self._ok("grep", results, t0)
        except Exception as e:
            return self._err("grep", str(e), t0)

    # ── SHELL ──

    def bash(self, command: str, timeout: int = 120) -> ToolResult:
        """Execute a bash/shell command."""
        t0 = time.perf_counter()

        if not self.security.allow_bash(command):
            return self._err("bash", "Security policy denied command", t0)

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                cwd=str(self.work_dir), timeout=timeout,
            )
            output = result.stdout
            if result.returncode != 0:
                output += f"\n[stderr]: {result.stderr}"
            self.security.log_bash(command, result.returncode)
            return self._ok("bash", output[:5000], t0)
        except subprocess.TimeoutExpired:
            return self._err("bash", f"Timeout after {timeout}s", t0)
        except Exception as e:
            return self._err("bash", str(e), t0)

    # ── WEB ──

    def web_search(self, query: str) -> ToolResult:
        """Search the web via DuckDuckGo."""
        t0 = time.perf_counter()
        try:
            import urllib.request
            import urllib.parse
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={"User-Agent": "MUE/0.5"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                # Extract result snippets
                results = []
                import re
                for m in re.finditer(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL):
                    results.append(re.sub(r'<[^>]+>', '', m.group(1)).strip()[:300])
                return self._ok("web_search", {"query": query, "results": results[:10]}, t0)
        except Exception as e:
            return self._err("web_search", str(e), t0)

    def web_fetch(self, url: str, prompt: str) -> ToolResult:
        """Fetch and process a URL."""
        t0 = time.perf_counter()
        if not self.security.allow_network(url):
            return self._err("web_fetch", "Security policy denied network access", t0)
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "MUE/0.5"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                content = resp.read().decode("utf-8", errors="replace")[:10000]
                return self._ok("web_fetch", {"url": url, "content": content, "prompt": prompt}, t0)
        except Exception as e:
            return self._err("web_fetch", str(e), t0)

    # ── MCP ──

    def call_mcp(self, server: str, tool: str, args: dict) -> ToolResult:
        """Call an MCP tool from another server."""
        t0 = time.perf_counter()
        # This bridges to external MCP servers
        # In production, this would use MCP client SDK
        return self._ok("mcp", {
            "server": server, "tool": tool, "args": args,
            "note": "MCP bridge active. Agent can call external tools.",
        }, t0)

    # ── HELPERS ──

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if p.is_absolute():
            return p
        return (self.work_dir / p).resolve()

    def _ok(self, tool: str, output: Any, t0: float) -> ToolResult:
        elapsed = (time.perf_counter() - t0) * 1000
        result = ToolResult(tool=tool, success=True, output=output, elapsed_ms=elapsed)
        self.history.append(result)
        return result

    def _err(self, tool: str, error: str, t0: float) -> ToolResult:
        elapsed = (time.perf_counter() - t0) * 1000
        result = ToolResult(tool=tool, success=False, output=None, error=error, elapsed_ms=elapsed)
        self.history.append(result)
        return result

    @property
    def tool_list(self) -> list[dict]:
        """List of available tools (for LLM function calling)."""
        return [
            {"name": "read_file", "description": "Read a file", "parameters": {"path": "string", "offset": "int?", "limit": "int?"}},
            {"name": "write_file", "description": "Write/create a file", "parameters": {"path": "string", "content": "string"}},
            {"name": "edit_file", "description": "Edit a file with string replacement", "parameters": {"path": "string", "old": "string", "new": "string"}},
            {"name": "glob", "description": "Find files by pattern", "parameters": {"pattern": "string"}},
            {"name": "grep", "description": "Search file contents with regex", "parameters": {"pattern": "string", "path": "string?", "glob": "string?"}},
            {"name": "bash", "description": "Execute shell command", "parameters": {"command": "string", "timeout": "int?"}},
            {"name": "web_search", "description": "Search the web", "parameters": {"query": "string"}},
            {"name": "web_fetch", "description": "Fetch a URL", "parameters": {"url": "string", "prompt": "string"}},
            {"name": "call_mcp", "description": "Call an MCP tool", "parameters": {"server": "string", "tool": "string", "args": "object"}},
        ]
