# claudeff preflight

> One approval, zero interruptions. Claude asks for permission once — then runs unattended.

## The problem

Every `Bash` or `Write` tool call prompts you for approval. For a 30-step task, that's 30 interruptions. You can't leave Claude running while you sleep.

## The fix

On the **first tool call** of each session, the preflight hook:

1. Reads your task from the transcript
2. Calls Claude Haiku to enumerate every file and shell permission the task will need
3. Shows a **single approval UI** — one glance, one keypress
4. Saves the manifest to `~/.claude/preflight/<session_id>.json`
5. Auto-approves every subsequent tool call within the manifest
6. **Blocks** anything outside — with a clear reason

```
╔════════════════════════════════════════════════════════╗
║     claudeff · Pre-flight Permission Manifest          ║
╚════════════════════════════════════════════════════════╝

  Task: Build and test the React auth flow
  Risk: MEDIUM — runs npm install and build scripts

  Read access:
    · src/**
    · package.json
    · tsconfig.json

  Write access:
    · src/**
    · dist/**

  Shell commands:
    · npm .*
    · git .*
    · node .*

  ────────────────────────────────────────────────────────
  [A]pprove  [S]kip checks  [D]eny session
  ────────────────────────────────────────────────────────

  Choice [A]:
```

Press `A` → Claude runs the full task without another prompt.

## Demo GIF description

*Screen recording: User types a multi-step task into Claude Code. Claude's first tool call triggers the preflight UI in the terminal. User presses Enter (accepts default "A"). Claude then executes 25 tool calls — Bash, Write, Edit — with zero additional prompts. Task completes while user walks away.*

## Install

```bash
# Everything at once (recommended)
git clone https://github.com/Rishi1314/claudeff && python claudeff/install.py

# Just this tool
python claudeff/hooks/preflight/install.py
```

The hook registers itself in `~/.claude/settings.json`.

## Uninstall

```bash
python claudeff/hooks/preflight/install.py --uninstall
```

## Disable for one session

```bash
CLAUDEFF_PREFLIGHT=0 claude "your task"
```

## How it works

- **Hook type**: `PreToolUse` on all tools (`matcher: ""`)
- **Session state**: `~/.claude/preflight/<session_id>.json`
- **Analysis model**: Claude Haiku (fast, cheap — typically <1s, ~$0.001/session)
- **Fallback**: If analysis fails, shows UI with "grant all" option — never silently blocks

## Manifest format

```json
{
  "session_id": "abc123",
  "approved_at": "2026-05-31T02:00:00",
  "task_summary": "Build and test the React auth flow",
  "risk_level": "medium",
  "risk_reason": "runs npm install and build scripts",
  "permissions": {
    "files": {
      "read": ["src/**", "package.json", "tsconfig.json"],
      "write": ["src/**", "dist/**"]
    },
    "shell": {
      "allowed_patterns": ["npm .*", "git .*", "node .*"],
      "blocked_patterns": []
    },
    "network": false
  }
}
```

## Requirements

- Python 3.10+
- `anthropic` Python SDK (`pip install anthropic`)
- `ANTHROPIC_API_KEY` in environment
