#!/usr/bin/env python3
"""
Install claudeff file-server MCP into ~/.claude/settings.json.

Run: python install.py
Run: python install.py --uninstall
"""

import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# npm.cmd required on Windows; bare "npm" isn't on the subprocess PATH
NPM = "npm.cmd" if sys.platform == "win32" else "npm"

SERVER_DIR = Path(__file__).parent
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
SERVER_NAME = "claudeff-file-server"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text())
        except Exception:
            pass
    return {}


def save_settings(s: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(s, indent=2))


def install():
    print("Installing claudeff file-server MCP…")

    print("  Building TypeScript…")
    subprocess.run([NPM, "install"], cwd=SERVER_DIR, check=True, capture_output=True)
    subprocess.run([NPM, "run", "build"], cwd=SERVER_DIR, check=True, capture_output=True)
    print("  ✓ Built")

    dist = SERVER_DIR / "dist" / "index.js"
    if not dist.exists():
        print(f"  ✗ Build output not found: {dist}")
        sys.exit(1)

    settings = load_settings()
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}

    settings["mcpServers"][SERVER_NAME] = {
        "command": "node",
        "args": [str(dist)],
    }

    save_settings(settings)
    print(f"  ✓ MCP registered as '{SERVER_NAME}' in {SETTINGS_PATH}")
    print()
    print("Done! Restart Claude Code to activate.")
    print()
    print("Available tools:")
    print("  read_symbol    — extract a single function/class body")
    print("  file_outline   — signatures only, 80-95% token savings")
    print("  read_range     — line range slice")
    print("  search_symbols — find definitions across the codebase")
    print("  file_diff      — what changed since first access")


def uninstall():
    print(f"Uninstalling '{SERVER_NAME}'…")
    settings = load_settings()
    if SERVER_NAME in settings.get("mcpServers", {}):
        del settings["mcpServers"][SERVER_NAME]
        save_settings(settings)
        print("  ✓ Removed from settings")
    else:
        print("  Not found in settings — nothing to do")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
