#!/usr/bin/env python3
"""
claudeff preflight — Pre-flight permission manifest hook for Claude Code.

On the first tool call of a session, calls Claude Haiku to enumerate the
permissions the task will need, shows a single approval UI, then auto-approves
or blocks all subsequent tool calls based on the saved manifest.

Install: python install.py
Disable: set CLAUDEFF_PREFLIGHT=0
"""

import sys
import json
import os
import re
import fnmatch
from pathlib import Path
from datetime import datetime

MANIFEST_DIR = Path.home() / ".claude" / "preflight"
VERSION = "0.1.0"


# ── Manifest I/O ──────────────────────────────────────────────────────────────

def load_manifest(session_id: str) -> dict | None:
    path = MANIFEST_DIR / f"{session_id}.json"
    try:
        return json.loads(path.read_text()) if path.exists() else None
    except Exception:
        return None


def save_manifest(session_id: str, manifest: dict):
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    (MANIFEST_DIR / f"{session_id}.json").write_text(json.dumps(manifest, indent=2))


# ── Path / command matching ───────────────────────────────────────────────────

def path_matches(file_path: str, patterns: list) -> bool:
    """Glob-match a file path against a list of patterns (handles Windows paths)."""
    normalized = file_path.replace("\\", "/")
    name = Path(file_path).name
    for pat in patterns:
        pat = pat.replace("\\", "/")
        if fnmatch.fnmatch(normalized, pat):
            return True
        if fnmatch.fnmatch(name, pat):
            return True
        # Try matching trailing portion: "src/**" should match "/abs/path/src/foo.ts"
        if "/" in pat:
            pat_root = pat.split("/")[0]
            if pat_root in normalized:
                tail = normalized[normalized.index(pat_root):]
                if fnmatch.fnmatch(tail, pat):
                    return True
    return False


def check_tool(tool_name: str, tool_input: dict, manifest: dict) -> tuple:
    """Returns (allowed: bool, reason: str)."""
    perms = manifest.get("permissions", {})

    READ_TOOLS  = {"Read", "Glob", "Grep"}
    WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

    if tool_name in READ_TOOLS:
        fp = tool_input.get("file_path") or tool_input.get("path") or ""
        if not fp or path_matches(fp, perms.get("files", {}).get("read", ["**"])):
            return True, "allowed"
        return False, f"Read not permitted: {fp}"

    if tool_name in WRITE_TOOLS:
        fp = tool_input.get("file_path", "")
        if path_matches(fp, perms.get("files", {}).get("write", [])):
            return True, "allowed"
        return False, f"Write not permitted: {fp}"

    if tool_name == "Bash":
        cmd = tool_input.get("command", "").strip()
        shell = perms.get("shell", {})
        for pat in shell.get("blocked_patterns", []):
            if re.search(pat, cmd, re.IGNORECASE):
                return False, f"Blocked by pattern '{pat}'"
        allowed = shell.get("allowed_patterns", [])
        if not allowed:
            return True, "no shell restrictions"
        for pat in allowed:
            try:
                if re.match(pat, cmd):
                    return True, "allowed"
            except re.error:
                if fnmatch.fnmatch(cmd.split()[0] if cmd.split() else cmd, pat):
                    return True, "allowed"
        return False, "Command outside approved scope"

    # Agent, WebFetch, WebSearch, etc. — unrestricted by default
    return True, "unrestricted tool"


# ── Claude Haiku analysis ─────────────────────────────────────────────────────

def _extract_task(transcript_path: str, tool_name: str, tool_input: dict) -> str:
    """Pull user's first message from transcript."""
    if transcript_path:
        try:
            raw = json.loads(Path(transcript_path).read_text())
            messages = raw if isinstance(raw, list) else raw.get("messages", [])
            for msg in messages:
                if msg.get("role") != "human":
                    continue
                content = msg.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            return block["text"][:1200]
                elif isinstance(content, str):
                    return content[:1200]
        except Exception:
            pass
    return f"Session starting with {tool_name}: {str(tool_input)[:300]}"


def analyze_with_claude(transcript_path: str, tool_name: str, tool_input: dict) -> dict | None:
    """Call Claude Haiku to enumerate permissions. Returns analysis dict or None."""
    try:
        import anthropic
    except ImportError:
        _err("anthropic not installed — run: pip install anthropic")
        return None

    task = _extract_task(transcript_path, tool_name, tool_input)

    prompt = f"""Analyze this Claude Code session and enumerate the file/shell permissions it will need.

User task: {task}

First tool: {tool_name}
Input (truncated): {json.dumps(tool_input)[:400]}

Output ONLY valid JSON — no markdown fences, no explanation:
{{
  "task_summary": "one-line description under 80 chars",
  "permissions": {{
    "files": {{
      "read":  ["glob patterns — e.g. src/**, *.json, README.md"],
      "write": ["glob patterns — e.g. src/**, dist/**"]
    }},
    "shell": {{
      "allowed_patterns": ["regex — e.g. npm .*, git .*, python .*"],
      "blocked_patterns": ["regex for explicitly dangerous ops — usually empty"]
    }},
    "network": false
  }},
  "risk_level": "low",
  "risk_reason": "one sentence"
}}

Rules:
- risk=low for read-only or standard writes; medium for package installs/builds; high for destructive/rm ops
- Infer paths from the task. Use ** for recursive. Be specific, not overly broad.
- blocked_patterns should only contain genuinely dangerous ops (rm -rf /, sudo, etc.)"""

    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            text = m.group(0)
        return json.loads(text)
    except Exception as e:
        _err(f"Analysis failed: {e}")
        return None


# ── Terminal UI ───────────────────────────────────────────────────────────────

_NO_COLOR = os.environ.get("NO_COLOR") or not sys.stderr.isatty()
_ANSI = {
    "bold": "\033[1m", "dim": "\033[2m",
    "green": "\033[92m", "yellow": "\033[93m",
    "red": "\033[91m", "cyan": "\033[96m",
    "reset": "\033[0m",
}


def _c(color: str, text: str) -> str:
    return text if _NO_COLOR else f"{_ANSI.get(color,'')}{text}{_ANSI['reset']}"


def _err(msg: str):
    print(f"[preflight] {msg}", file=sys.stderr)


def show_approval_ui(analysis: dict) -> str:
    """Render approval UI to stderr. Returns 'approve' | 'skip' | 'deny'."""
    perms   = analysis.get("permissions", {})
    risk    = analysis.get("risk_level", "unknown")
    r_color = {"low": "green", "medium": "yellow", "high": "red"}.get(risk, "yellow")

    W = 56
    sep = _c("bold", "─" * W)

    def section(label: str, items: list, color: str):
        if not items:
            return
        _err(f"\n  {_c(color, label)}")
        for item in items[:8]:
            _err(f"    {_c('dim', '·')} {item}")
        if len(items) > 8:
            _err(f"    {_c('dim', f'… and {len(items)-8} more')}")

    _err("")
    _err(_c("bold", "╔" + "═" * W + "╗"))
    _err(_c("bold", "║") + _c("bold", "   claudeff · Pre-flight Permission Manifest   ".center(W)) + _c("bold", "║"))
    _err(_c("bold", "╚" + "═" * W + "╝"))
    _err(f"\n  {_c('bold','Task:')} {analysis.get('task_summary','Unknown')}")
    _err(f"  {_c('bold','Risk:')} {_c(r_color, risk.upper())} — {analysis.get('risk_reason','')}")

    files = perms.get("files", {})
    section("Read access:",   files.get("read", []),  "cyan")
    section("Write access:",  files.get("write", []), "yellow")
    shell = perms.get("shell", {})
    section("Shell commands:", shell.get("allowed_patterns", []), "cyan")
    section("Blocked:",        shell.get("blocked_patterns", []),  "red")

    _err(f"\n  {sep}")
    _err(f"  {_c('green','[A]pprove')}  {_c('dim','[S]kip checks')}  {_c('red','[D]eny session')}")
    _err(f"  {sep}\n")

    try:
        choice = input("  Choice [A]: ").strip().lower() or "a"
    except (EOFError, KeyboardInterrupt):
        return "deny"

    return "approve" if choice in ("a", "approve") else \
           "skip"    if choice in ("s", "skip")    else "deny"


# ── Output helpers ────────────────────────────────────────────────────────────

def _allow():
    sys.exit(0)


def _block(reason: str):
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def _permissive_manifest() -> dict:
    return {
        "permissions": {
            "files": {"read": ["**"], "write": ["**"]},
            "shell": {"allowed_patterns": [".*"], "blocked_patterns": []},
            "network": True,
        },
        "task_summary": "All permissions granted (analysis skipped)",
        "risk_level": "unknown",
        "risk_reason": "Analysis unavailable",
    }


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        _allow()

    if os.environ.get("CLAUDEFF_PREFLIGHT", "1") == "0":
        _allow()

    session_id      = data.get("session_id", "unknown")
    tool_name       = data.get("tool_name", "")
    tool_input      = data.get("tool_input", {})
    transcript_path = data.get("transcript_path", "")

    manifest = load_manifest(session_id)

    # ── First call: analyze + present UI ──────────────────────────────────────
    if manifest is None:
        _err("Analyzing session permissions…")

        analysis = analyze_with_claude(transcript_path, tool_name, tool_input)

        if analysis is None:
            _err("Could not analyze — granting all permissions.")
            manifest = {"session_id": session_id, "approved_at": datetime.now().isoformat(),
                        **_permissive_manifest()}
            save_manifest(session_id, manifest)
            _allow()

        decision = show_approval_ui(analysis)

        if decision == "approve":
            manifest = {"session_id": session_id, "approved_at": datetime.now().isoformat(),
                        **analysis}
            save_manifest(session_id, manifest)
            _err(_c("green", "✓ Manifest approved — session authorized.\n"))
            _allow()

        elif decision == "skip":
            manifest = {"session_id": session_id, "approved_at": datetime.now().isoformat(),
                        **_permissive_manifest()}
            save_manifest(session_id, manifest)
            _err(_c("yellow", "⚠ Permission checks skipped.\n"))
            _allow()

        else:
            _block("Session denied by user at pre-flight check")

    # ── Subsequent calls: enforce manifest ────────────────────────────────────
    else:
        allowed, reason = check_tool(tool_name, tool_input, manifest)
        if not allowed:
            _err(_c("red", f"✗ Blocked: {reason}"))
            _block(reason)
        _allow()


if __name__ == "__main__":
    main()
