# claudeff

A suite of Claude Code tools, MCPs, and hooks that solve real pain points for both beginner and seasoned users. Goal: features so good that developers share them online unprompted.

## What this project is

A collection of independently shippable tools that improve Claude Code without touching Claude's core behavior. Each tool is a standalone deliverable — MCP server, hook script, or CLI wrapper. They compose but don't depend on each other.

## Build priority

1. ~~**Pre-flight permission manifest**~~ — **DONE** (`hooks/preflight/`)
2. **Bug autopsy** — dramatic before/after, demonstrable in 30s, universal pain
3. **Speculative execution** — solves trust problem for all users, easy to demo
4. ~~**Smart MCP file server**~~ — **DONE** (`mcp/file-server/`)
5. ~~**Allow-all permissions helper**~~ — **DONE** (`cli/allow-all/`)
6. ~~**One-command installer**~~ — **DONE** (`install.py`)
7. Everything else in TODO.md

## Architecture principles

- Each tool ships independently. No shared runtime required.
- MCP servers for anything that replaces or augments Claude's file/search tools
- Claude Code hooks (PreToolUse / PostToolUse / Stop) for interception and guardrails
- No cloud dependency unless the feature explicitly requires it
- Tools must work with the existing Claude Code CLI — no forks, no patches

## Tech stack decisions

- **MCP servers**: TypeScript (Node) — aligns with Claude Code's own stack, best MCP SDK support
- **Hook scripts**: Python or shell — hooks are just executables, keep them simple
- **AST/symbol indexing**: tree-sitter (available in both TS and Python)
- **Git operations**: simple-git (TS) or GitPython (Python)
- Language TBD per tool — confirm with user before starting each one

## Tool specs

### Pre-flight permission manifest ✓ SHIPPED
- **Install**: `python hooks/preflight/install.py`
- **Disable**: `CLAUDEFF_PREFLIGHT=0`
- Hook: `PreToolUse` on all tools — fires once per session
- Calls Claude Haiku to enumerate needed permissions from the transcript
- Presents a single approval UI (Approve / Skip / Deny)
- Writes manifest to `~/.claude/preflight/<session_id>.json`
- Subsequent calls auto-approve if within manifest, block (with reason) if outside
- Falls back to "grant all" if Haiku analysis fails — never silently breaks

### Bug autopsy
- Input: bug description (free text) or GitHub issue URL
- Steps: reproduce → grep codebase for relevant symbols → `git log -S` to find when they changed → summarize each candidate commit → rank by likelihood → explain the "why" using commit message + diff context → suggest minimal fix
- Output: structured report with commit hash, author reasoning, and fix suggestion

### Speculative execution
- Intercept any write/edit/delete operation
- Clone affected files to a temp sandbox
- Apply changes in sandbox
- Run relevant tests against sandbox
- Show: diff + test results + risk score
- Prompt: Apply / Reject / Modify
- On apply: write to real files

### Allow-all permissions helper ✓ SHIPPED
- **Run**: `python cli/allow-all/allow_all.py`
- Patches `~/.claude/settings.json` to add all 14 standard tools to `permissions.allow`
- Safe merge — preserves existing settings, idempotent, no restart needed
- Flags: `--dry-run` (preview), `--undo` (remove added permissions), `--path` (custom settings file)

### Smart MCP file server ✓ SHIPPED
- **Install**: `python mcp/file-server/install.py` (runs `npm install && tsc`, registers MCP)
- MCP name: `claudeff-file-server`
- Tools: `read_symbol`, `read_range`, `file_outline`, `search_symbols`, `file_diff`
- Regex-based symbol extraction for TS/JS/Python; tree-sitter upgrade path ready
- `file_outline` — 80-95% token savings vs. reading whole files
- `file_diff` — snapshots on first access, returns unified diff on subsequent calls
- `search_symbols` — walks directory tree, returns file:line matches (no full-file reads)

### Goal anchoring hook
- `PreToolUse` hook that fires every N tool calls (configurable, default 15)
- Re-injects the original user task as a system reminder
- Detects drift: if current tool pattern diverges significantly from original intent, warns Claude

### Test loop detector
- `PostToolUse` hook on shell commands
- Tracks test run results in session state
- If same test suite fails 3 times with different fixes attempted: fires Stop event, outputs structured "stuck" report for user review

### CLAUDE.md generator + linter
- `generate`: scans repo (package.json, pyproject.toml, tsconfig, src structure, git log) → produces CLAUDE.md draft
- `lint`: checks for stale file paths, outdated package versions mentioned, entries over 2 sentences, missing build/test commands
- Ships as a CLI: `claudeff init`, `claudeff lint`

## File layout

```
claudeff/
  mcp/
    file-server/        # ✓ Smart MCP file server (read_symbol, file_outline, file_diff, ...)
  hooks/
    preflight/          # ✓ Pre-flight permission manifest (auto-approve / block)
    goal-anchor/        # (planned) Goal anchoring
    test-loop/          # (planned) Test loop detector
    speculative/        # (planned) Speculative execution
  cli/
    allow-all/          # ✓ Allow-all permissions helper (patches ~/.claude/settings.json)
    claudeff/           # (planned) Main CLI (init, lint, autopsy, ship)
  TODO.md
  CLAUDE.md
```

## What "done" looks like per tool

Each tool ships with:
- Working implementation
- A `README.md` with a 30-second demo GIF description (so user can record it)
- Install instructions (one command)
- Example config / usage

## User context

- User wants tools shareable on Reddit/LinkedIn/HN — prioritize dramatic before/after, visual demos, and one-command install
- Build one tool completely before starting the next
- Confirm language/stack choice with user before starting each tool
- Next tool to build: **Bug autopsy** (build priority #2)
