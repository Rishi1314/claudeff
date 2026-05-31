# claudeff TODO

## Done
- [x] Pre-flight permission manifest (`hooks/preflight/`) — Python hook, Claude Haiku analysis, terminal UI, session manifest, auto-approve/block
- [x] Smart MCP file server (`mcp/file-server/`) — TypeScript MCP, read_symbol, file_outline, read_range, search_symbols, file_diff
- [x] Allow-all permissions helper (`cli/allow-all/`) — patches ~/.claude/settings.json to allow all standard tools; supports --undo and --dry-run
- [x] One-command installer (`install.py`) — installs all tools in sequence; supports --uninstall and --dry-run
- [x] Bug autopsy (`cli/autopsy/`) — keyword extraction, git log -S pickaxe search, scored ranking; zero dependencies

## Next up (in priority order)

### Bug autopsy (`cli/autopsy/`) ✓ DONE
- [x] Input: free-text bug description or error message
- [x] Steps: keyword extraction → git log -S pickaxe per keyword → score by hits + message match + recency
- [x] Output: ranked report with files changed, score breakdown, and next-step git commands
- [x] Ships as: `python cli/autopsy/autopsy.py "error message"` (zero dependencies)

### Speculative execution (`hooks/speculative/`)
- [ ] Intercept Write/Edit/Bash(delete)
- [ ] Clone affected files to temp sandbox
- [ ] Apply changes, run relevant tests in sandbox
- [ ] Show: diff + test results + risk score
- [ ] Prompt: Apply / Reject / Modify

### Goal anchoring hook (`hooks/goal-anchor/`)
- [ ] Fire every N tool calls (configurable, default 15)
- [ ] Re-inject original user task as reminder
- [ ] Detect drift: warn if current tool pattern diverges from intent

### Test loop detector (`hooks/test-loop/`)
- [ ] PostToolUse on shell commands
- [ ] If same test fails 3x with different fixes: fire Stop, output "stuck" report

### CLAUDE.md generator + linter (`cli/claudeff/`)
- [ ] claudeff init: scan repo, produce CLAUDE.md draft
- [ ] claudeff lint: check stale paths, outdated versions, missing commands

## Backlog
- [ ] Demo GIF recordings for each tool
- [ ] npm package for file-server
- [ ] PyPI package for hooks
