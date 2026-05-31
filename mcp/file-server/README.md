# claudeff file-server

> Read symbols, not files. 80-95% fewer tokens on every lookup.

## The problem

Claude reads entire files to find one function. A 500-line `utils.ts` costs ~3,000 tokens every time Claude needs to check one helper. In a long session, this adds up to tens of thousands of wasted tokens — and slower, more expensive responses.

## The fix

The file-server MCP exposes surgical access tools:

| Tool | Instead of | Token savings |
|---|---|---|
| `read_symbol` | Read whole file to find one function | ~90% |
| `file_outline` | Read whole file to understand structure | ~80-95% |
| `read_range` | Read whole file when you know the line | ~70-90% |
| `search_symbols` | Grep + Read to find a definition | ~85% |
| `file_diff` | Re-read file to see what changed | ~95% |

## Demo GIF description

*Screen recording split view: left panel shows token counter, right shows Claude working. Claude uses `file_outline` on a 400-line file — token counter jumps 200. Then Claude uses native Read on the same file — token counter jumps 2,800. Caption: "14x fewer tokens." Next clip: Claude uses `search_symbols` to find a function definition across 50 files — returns in 0.3s with just the file path and line number.*

## Install

```bash
cd mcp/file-server
python install.py
```

Restart Claude Code. The tools appear as `read_symbol`, `file_outline`, etc.

## Uninstall

```bash
python install.py --uninstall
```

## Tools

### `file_outline`

Returns all symbol signatures and one-line docstrings — no bodies.

```
// src/auth/session.ts — outline (8 symbols)

function    createSession              L12-45    // Creates a new user session
function    destroySession             L47-58    // Destroys session by ID
class       SessionStore               L60-180   // In-memory session storage
method      get                        L72-80
method      set                        L82-95
method      delete                     L97-108
interface   SessionOptions             L110-120
type        SessionID                  L122
```

### `read_symbol`

Returns only the body of a named symbol.

```typescript
// src/auth/session.ts:12-45 — function createSession

export async function createSession(userId: string, opts: SessionOptions): Promise<Session> {
  const id = generateId();
  const session = { id, userId, createdAt: Date.now(), ...opts };
  store.set(id, session);
  return session;
}
```

### `file_diff`

First call: returns full file + snapshots it.  
Subsequent calls: returns only what changed.

```diff
--- src/auth/session.ts (before)
+++ src/auth/session.ts (after)
@@ -14,7 +14,7 @@
   const id = generateId();
-  const session = { id, userId, createdAt: Date.now(), ...opts };
+  const session = { id, userId, createdAt: Date.now(), expiresAt: Date.now() + opts.ttl, ...opts };
   store.set(id, session);
```

### `search_symbols`

```
Definitions of 'createSession':

src/auth/session.ts:12    function createSession
src/auth/session.test.ts:8  function createSession (mock)
```

## Requirements

- Node.js 18+
- npm
