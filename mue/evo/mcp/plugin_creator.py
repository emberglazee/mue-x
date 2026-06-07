"""MCP Plugin Creator — The agent creates its own MCP tools.

As MUE evolves, it can generate new MCP server plugins that extend
its capabilities. These plugins become available to any MCP client
(including Claude Code). The agent can create trading bots, data
fetchers, analysis tools — anything it can code, it can expose as MCP.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
import time


@dataclass
class MCPPlugin:
    """An MCP server plugin created by the agent."""
    name: str
    description: str
    tools: list[dict]  # [{"name": "...", "description": "...", "parameters": {...}}]
    source_path: Path
    created_at: float = field(default_factory=time.time)
    version: int = 1
    usage_count: int = 0


class PluginCreator:
    """The agent creates, deploys, and manages its own MCP plugins."""

    def __init__(self, plugins_dir: Path, power_tools):
        self.plugins_dir = Path(plugins_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.tools = power_tools
        self.plugins: dict[str, MCPPlugin] = {}
        self._scan()

    def _scan(self):
        """Discover existing plugins."""
        for plugin_dir in self.plugins_dir.iterdir():
            if plugin_dir.is_dir():
                manifest = plugin_dir / "mcp_manifest.json"
                if manifest.exists():
                    try:
                        data = json.loads(manifest.read_text())
                        plugin = MCPPlugin(
                            name=data["name"],
                            description=data["description"],
                            tools=data.get("tools", []),
                            source_path=plugin_dir,
                        )
                        self.plugins[plugin.name] = plugin
                    except (json.JSONDecodeError, KeyError):
                        pass

    def create_plugin(self, name: str, description: str,
                      code: str, tool_defs: list[dict]) -> MCPPlugin | None:
        """Create a new MCP plugin from generated code."""
        plugin_dir = self.plugins_dir / name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Write the plugin server code
        server_py = plugin_dir / "server.py"
        server_py.write_text(code, encoding="utf-8")

        # Write manifest
        manifest = {
            "name": name,
            "description": description,
            "tools": tool_defs,
            "version": 1,
            "created_at": time.time(),
        }
        (plugin_dir / "mcp_manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # Write requirements if any
        reqs = plugin_dir / "requirements.txt"
        reqs.write_text("mcp>=1.0\n", encoding="utf-8")

        plugin = MCPPlugin(
            name=name,
            description=description,
            tools=tool_defs,
            source_path=plugin_dir,
        )
        self.plugins[name] = plugin
        return plugin

    def get_mcp_config(self) -> dict:
        """Generate MCP configuration for all plugins."""
        config = {"mcpServers": {}}
        for name, plugin in self.plugins.items():
            config["mcpServers"][f"mue-plugin-{name}"] = {
                "command": "python",
                "args": [str(plugin.source_path / "server.py")],
                "description": plugin.description,
            }
        return config

    def write_mcp_config(self, output_path: Path):
        """Write MCP configuration to a JSON file."""
        config = self.get_mcp_config()
        output_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    @property
    def stats(self) -> dict:
        return {
            "total_plugins": len(self.plugins),
            "plugin_names": list(self.plugins.keys()),
            "total_tools": sum(len(p.tools) for p in self.plugins.values()),
        }
