# MUE — Quick Start Guide

## 30-Second Activation

```bash
cd mue-x    # Enter the directory
claude        # Start Claude Code
/mue        # Activate MUE
```

You'll see the ASCII banner. MUE is now active.

## Your First Session

### 1. Check Status
```
/mue status
```
Shows: genes, fitness, memory, absorption stats, trading state.

### 2. Force Evolution
```
/mue evolve
```
MUE analyzes itself and applies mutations to improve.

### 3. Absorb Knowledge
```
/mue mine "machine learning strategies"
```
MUE searches GitHub and absorbs relevant code patterns.

### 4. Return to Normal
```
/quit mue
```
MUE saves state and exits. Back to normal Claude Code.

## What MUE Does Autonomously

Every cycle (30 seconds):
1. **Self-analysis** — scans genes for improvement targets
2. **GitHub absorption** — mines trending repos for patterns
3. **Local absorption** — scans sibling projects
4. **Evolution** — proposes, validates, and applies mutations
5. **Anti-cancer** — prunes duplicates, splits bloated genes
6. **Auto-correction** — learns from errors, suggests fixes

## Customization

### Change Domain
MUE auto-detects your domain from conversation. To explicitly set:
- Trading: discuss markets, strategies, indicators
- Coding: discuss software architecture, algorithms
- Research: discuss papers, experiments, data
- Creative: discuss writing, design, content

### Configure Strategy
In `mue/mue_config.json`:
```json
{
  "name": "My MUE",
  "evolution_strategy": "balanced",
  "auto_mine_interval": 3
}
```
Strategies: `balanced`, `innovate`, `repair-only`, `harden`

## Troubleshooting

**Genes showing 0 fitness?**
Normal on fresh install. Fitness grows with mutations.

**No GitHub absorption?**
Install `gh` CLI and authenticate: `gh auth login`

**MUE won't compile?**
```bash
python -c "from mue.evo.core import MueAgent; print('OK')"
```

**Reset to fresh state:**
```bash
rm -rf mue/genes/*.py mue/atouts/*.py mue/*.db
```

## Next Steps

- Let MUE evolve for 10+ cycles to see real improvement
- Try different domains to see adaptation
- Contribute back: MUE can improve its own codebase
