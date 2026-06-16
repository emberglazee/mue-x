# MUE-X for Copilot CLI

MUE-X works with GitHub Copilot CLI via its skill system. Copilot CLI supports skills as markdown files with a `skill` tool (equivalent to Claude Code's `Skill` tool).

## Setup

1. Clone MUE-X:
```bash
git clone https://github.com/KorroAi/mue-x.git ~/.copilot/mue-x
```

2. Register the skill in Copilot CLI's skill registry:
```bash
copilot skill register --name mue --path ~/.copilot/mue-x/.claude/skills/mue/SKILL.md
```

3. Activate: `/mue` in any Copilot CLI session.

## Tool Mapping

| Claude Code Tool | Copilot CLI Equivalent |
|-----------------|----------------------|
| Read | read |
| Write | write |
| Edit | edit |
| Bash | exec or shell |
| Glob | glob or search |
| Grep | grep |

## Notes
- Copilot CLI's agent system may have different concurrency limits for multi-agent operations (swarm module)
- The `mue/evo/core.py` brain is platform-agnostic — only the tool calls vary
- For headless mode: `python -m mue` bypasses Copilot CLI entirely
