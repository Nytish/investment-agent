# APEX Relay Mode — Dual-Session Handoff Protocol

When a Claude Code session's context window fills, this protocol lets Session A hand work to Session B with zero loss of state.

## Why it exists

Large AI coding sessions accumulate context. When context fills:
- The LLM can no longer reason about early decisions
- Tool results from the beginning of the session are dropped
- A new session starts blank — and has to rediscover what was built

Relay Mode solves this by capturing all project state into a portable checkpoint before the old session ends.

## Quick start

**Session A** — when context is ~50% full or work is stopping:
```bash
cd /home/claude/apex2
python handoff.py --checkpoint
```
Outputs: `/tmp/apex_checkpoint.json`

**Session B** — in a new Claude Code session:
```bash
cd /home/claude/apex2
python handoff.py --restore /tmp/apex_checkpoint.json
```
Session B reads the resume instructions and continues from the exact next task.

## What the checkpoint captures

```json
{
  "as_of": "2026-10-22T14:00:00",
  "completed_phases": ["Phase 0: ...", "Phase 4: ..."],
  "tests": {"summary": "39 passed in 0.10s", "passed": 39, "failed": 0},
  "bugs": [{"id": "BUG-001", "status": "FIXED", ...}],
  "files": {"core/market_feed.py": "EXISTS", "core/tax_engine.py": "MISSING"},
  "next_3_tasks": ["Phase 1: Port TaxEngine..."],
  "key_context": {"savings": "€50,000...", "fire_target": "€600K by age 47"},
  "security_constraints": [...]
}
```

## Commands

| Command | Purpose |
|---------|---------|
| `python handoff.py --summary` | Compact JSON state (for quick reading) |
| `python handoff.py --checkpoint` | Write full checkpoint to `/tmp/apex_checkpoint.json` |
| `python handoff.py --restore FILE` | Print human-readable resume instructions |

## Protocol for Claude sessions

### Session A responsibilities
1. When context token usage exceeds ~50%, run `--checkpoint`
2. Note the checkpoint path in a final message
3. Run `python -m pytest tests/ -v` to confirm all green before handoff

### Session B responsibilities
1. First action: `python handoff.py --restore /tmp/apex_checkpoint.json`
2. Read the resume instructions fully
3. Fix any OPEN bugs listed before starting new work
4. Run pytest to verify state: `python -m pytest tests/ -v`
5. Implement next task from the list

## Sharing the checkpoint across machines

The checkpoint is JSON — copy it freely:

```bash
# From Mac Mini M4 (running Mac session) to linux machine:
scp /tmp/apex_checkpoint.json user@linux-machine:/tmp/apex_checkpoint.json

# Or paste the JSON content directly into a new Claude session as context
```

## When to trigger handoff

- Context usage > 50% (visible in Claude Code as token count)
- Before ending a session mid-task
- Before switching machines (e.g., Mac Mini M4 ↔ Linux workstation)
- After completing a full phase (natural checkpoint moment)
