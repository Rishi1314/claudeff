# claudeff

> Claude Code tools so good developers share them unprompted.

A suite of independently installable tools that fix real Claude Code pain points — pre-flight permissions, surgical file access, instant bug archaeology, and zero-prompt operation.

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

### Bug autopsy
**`cli/autopsy/`**

Paste an error message — get the commits most likely to have introduced it, ranked by likelihood.

```
$ python cli/autopsy/autopsy.py "TypeError: Cannot read properties of undefined (reading 'sessionId')"

Searching 6 keyword(s): read, properties, session, TypeError, sessionId ...
  3 candidate commit(s) found.

════════════════════════════════════════════════════════════════
  BUG AUTOPSY
════════════════════════════════════════════════════════════════
  #1  a1b2c3d  refactor: restructure session token handling
      Author  : Jane Doe  |  2024-01-14  (2 days ago)
      Score   : 14.0  |  keywords in code: session, sessionId
      Changed : src/auth/session.ts, src/auth/token.ts
      Inspect : git show a1b2c3d

  Next steps: git show a1b2c3d  ·  git bisect start
════════════════════════════════════════════════════════════════
```

How it works: extracts symbols from the error → `git log -S` pickaxe search (finds commits that *changed* those strings) → scores by hit count + recency → prints ranked report with bisect commands.

Zero dependencies. No API key. Runs anywhere git is installed.

```bash
python cli/autopsy/autopsy.py "your error message"
python cli/autopsy/autopsy.py "login fails after token refresh" --top 10
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
| autopsy | 3.8+ | — |
| preflight | 3.10+ | — |
| file-server | 3.9+ | 18+ |

## What's next

- **Speculative execution** — run changes in a sandbox, show diff + test results before applying
- **Goal anchoring hook** — re-inject the original task every N tool calls to prevent drift
- **Test loop detector** — catch when Claude is stuck retrying the same failing test

See [TODO.md](TODO.md) for the full roadmap.
