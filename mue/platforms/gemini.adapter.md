# MUE-X for Gemini CLI

MUE-X works with Gemini CLI via the `activate_skill` tool. Gemini CLI skills are loaded from `.gemini/skills/` and use the same markdown-based activation as Claude Code skills.

## Setup

1. Copy MUE-X to your project or global skills:
```bash
git clone https://github.com/KorroAi/mue-x.git ~/.gemini/mue-x
```

2. Add to your `.gemini/skills/` or `GEMINI.md`:
```markdown
# In GEMINI.md or project config:
When the user types `/mue`, invoke activate_skill("mue") to load the MUE-X agent.
The skill definition is at `~/.gemini/mue-x/.claude/skills/mue/SKILL.md`.
```

3. All MUE-X commands work identically:
- `/mue` — Activate
- `/mue status` — State snapshot
- `/mue evolve` — Force evolution
- `/mue mine "query"` — GitHub absorption

## Tool Mapping

| Claude Code Tool | Gemini CLI Equivalent |
|-----------------|---------------------|
| Read | read_file |
| Write | write_file |
| Edit | edit_file |
| Bash | run_command |
| Glob | search_files |
| Grep | search_content |

MUE-X's mutation pipeline uses these tools — they work the same on both platforms.

## Limitations

- Gemini CLI's skill activation is slightly different (no `Skill` tool, uses `activate_skill`)
- The `SKILL.md` is the same format — only the invocation changes
- Python backend (`mue/evo/`) is identical — no changes needed
