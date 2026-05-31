# claudeff

> Claude Code tools so good developers share them unprompted.

A suite of independently installable tools that fix real Claude Code pain points — pre-flight permissions, surgical file access, and zero-prompt operation.

## Install everything (one line)

```bash
git clone https://github.com/Rishi1314/claudeff && python claudeff/install.py
```

Requires Python 3.10+ and Node 18+. Writes to `~/.claude/settings.json` — applies to every Claude Code session globally.

---

## Tools

### Pre-flight permission manifest
**`hooks/preflight/`**

Claude asks for all permissions once, upfront — then runs the entire task unattended.

Instead of 30 approval prompts mid-task, you get one:

```
╔════════════════════════════════════════════════════════╗
║     claudeff · Pre-flight Permission Manifest          ║
╚════════════════════════════════════════════════════════╝

  Task: Build and test the React auth flow
  Risk: MEDIUM — runs npm install and build scripts

  Shell:  npm .*  ·  git .*  ·  node .*
  Write:  src/**  ·  dist/**

  [A]pprove  [S]kip  [D]eny
  Choice [A]:
```

Press Enter. Claude runs 25 tool calls without another prompt.

```bash
python claudeff/hooks/preflight/install.py
```

---

### Smart MCP file server
**`mcp/file-server/`**

Read symbols, not files. 80–95% fewer tokens on every lookup.

| Tool | What it replaces | Savings |
|------|-----------------|---------|
| `file_outline` | Read whole file to understand structure | ~90% |
| `read_symbol` | Read whole file to find one function | ~90% |
| `read_range` | Read whole file for a known line range | ~80% |
| `search_symbols` | Grep + Read to find a definition | ~85% |
| `file_diff` | Re-read file to see what changed | ~95% |

```bash
python claudeff/mcp/file-server/install.py
```

---

### Allow-all permissions helper
**`cli/allow-all/`**

One command. No more permission prompts — ever.

```bash
python claudeff/cli/allow-all/allow_all.py
```

```
Added 14 permissions: Bash, Read, Edit, Write, WebFetch, Grep, Glob, LS, ...
Saved to ~/.claude/settings.json
```

Supports `--dry-run`, `--undo`, `--path`.

---

## Uninstall everything

```bash
python claudeff/install.py --uninstall
```

## Requirements

| Tool | Python | Node |
|------|--------|------|
| allow-all | 3.9+ | — |
| preflight | 3.10+ | — |
| file-server | 3.9+ | 18+ |

## What's next

- **Bug autopsy** — trace any bug to its culprit commit via `git log -S`, ranked by likelihood
- **Speculative execution** — run changes in a sandbox, show diff + test results before applying
- **Goal anchoring hook** — re-inject the original task every N tool calls to prevent drift

See [TODO.md](TODO.md) for the full roadmap.
