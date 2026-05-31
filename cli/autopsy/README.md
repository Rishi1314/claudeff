# Bug autopsy

Paste an error message — get a ranked list of the commits most likely to have introduced it.

No API key. No cloud. Pure git + grep.

## Demo

```
$ python autopsy.py "TypeError: Cannot read properties of undefined (reading 'sessionId')"

Searching 6 keyword(s): read, properties, reading, session, TypeError, sessionId
  3 unique candidate commit(s) found.

════════════════════════════════════════════════════════════════
  BUG AUTOPSY
════════════════════════════════════════════════════════════════
  Query    : TypeError: Cannot read properties of undefined (reading 'sessionId')
  Keywords : read, properties, reading, session, TypeError, sessionId

  3 suspect commit(s) ranked by likelihood:

────────────────────────────────────────────────────────────────
  #1  a1b2c3d  refactor: restructure session token handling
      Author  : Jane Doe  |  2024-01-14  (2 days ago)
      Score   : 14.0  |  keywords in code: session, sessionId
      Changed : src/auth/session.ts, src/auth/token.ts
      Inspect : git show a1b2c3d

  #2  ...

════════════════════════════════════════════════════════════════
  NEXT STEPS
════════════════════════════════════════════════════════════════
  1. Inspect top suspect:
       git show a1b2c3d
  2. See surrounding commits:
       git log --oneline a1b2c3d~3..a1b2c3d
  3. Bisect to confirm:
       git bisect start
       git bisect bad HEAD
       git bisect good <last-known-good-ref>
════════════════════════════════════════════════════════════════
```

## How it works

1. **Keyword extraction** — splits camelCase, strips stop-words, preserves compound identifiers like `sessionId`
2. **Pickaxe search** — runs `git log -S <keyword>` for each term; finds commits that *added or removed* that string from the codebase (not just "mentioned it in a comment")
3. **Scoring** — ranks by: number of keyword hits in code · keyword in commit message · recency
4. **Report** — shows top N suspects with files changed and actionable git commands

## Install (one command from repo root)

```bash
python install.py
```

Or verify autopsy standalone:

```bash
python cli/autopsy/install.py
```

## Usage

```bash
# Basic — paste the error message directly
python cli/autopsy/autopsy.py "TypeError: Cannot read properties of undefined"

# Show more suspects
python cli/autopsy/autopsy.py "login fails after token refresh" --top 10

# Different repo
python cli/autopsy/autopsy.py "AttributeError: 'NoneType'" --repo /path/to/other/repo
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--top N` | 5 | Show top N suspect commits |
| `--repo PATH` | `.` | Path to the git repository to search |

## Tips

- **Use the stack trace** — function names and symbol names (`sessionId`, `validateToken`) score much higher than generic words
- **Shorter is better** — `"session token refresh"` beats a 200-character stack trace; autopsy takes the first 12 keywords
- **Combine with bisect** — use autopsy to find a likely range, then `git bisect` to confirm the exact commit
