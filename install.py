#!/usr/bin/env python3
"""
claudeff one-command installer.

Installs all three claudeff tools into ~/.claude/settings.json:
  1. allow-all     — stop permission prompts
  2. file-server   — smart MCP file tools (needs Node 18+)
  3. preflight     — pre-flight permission manifest hook

Usage:
    python install.py
    python install.py --uninstall
    python install.py --dry-run     (allow-all preview only)
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

STEPS = [
    ("Allow-all permissions",    ROOT / "cli"   / "allow-all"  / "allow_all.py",        []),
    ("Smart MCP file server",    ROOT / "mcp"   / "file-server" / "install.py",          []),
    ("Pre-flight manifest hook", ROOT / "hooks" / "preflight"  / "install.py",           []),
]

UNINSTALL_STEPS = [
    ("Allow-all permissions",    ROOT / "cli"   / "allow-all"  / "allow_all.py",        ["--undo"]),
    ("Smart MCP file server",    ROOT / "mcp"   / "file-server" / "install.py",          ["--uninstall"]),
    ("Pre-flight manifest hook", ROOT / "hooks" / "preflight"  / "install.py",           ["--uninstall"]),
]


def run(label: str, script: Path, extra_args: list[str]) -> bool:
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    result = subprocess.run([sys.executable, str(script)] + extra_args)
    if result.returncode != 0:
        print(f"\n  ✗ {label} failed (exit {result.returncode})")
        return False
    return True


def main():
    uninstall = "--uninstall" in sys.argv
    dry_run   = "--dry-run"   in sys.argv

    steps = UNINSTALL_STEPS if uninstall else STEPS
    if dry_run and not uninstall:
        # pass --dry-run only to allow-all (the only script that supports it)
        steps = [
            (label, script, extra + ["--dry-run"] if "allow_all" in str(script) else extra)
            for label, script, extra in steps
        ]

    mode = "Uninstalling" if uninstall else "Installing"
    print(f"\nclaudeff — {mode} all tools\n")

    failed = []
    for label, script, extra in steps:
        if not run(label, script, extra):
            failed.append(label)

    print(f"\n{'='*50}")
    if failed:
        print(f"  Done with errors — {len(failed)} step(s) failed:")
        for f in failed:
            print(f"    ✗ {f}")
        sys.exit(1)
    else:
        total = len(steps)
        print(f"  Done — {total}/{total} tools {'uninstalled' if uninstall else 'installed'}.")
        if not uninstall:
            print("\n  Next: restart Claude Code to activate the MCP server.")


if __name__ == "__main__":
    main()
