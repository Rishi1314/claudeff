#!/usr/bin/env python3
"""
claudeff preflight installer.

Adds the preflight hook to ~/.claude/settings.json and installs dependencies.
Run: python install.py
Run: python install.py --uninstall  to remove
"""

import json
import subprocess
import sys
import os
from pathlib import Path

HOOK_SCRIPT = Path(__file__).parent / "preflight.py"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

PYTHON = sys.executable


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text())
        except Exception:
            pass
    return {}


def save_settings(settings: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def install():
    print("Installing claudeff preflight hook…")

    # Install anthropic SDK
    print("  Installing dependencies…")
    subprocess.run(
        [PYTHON, "-m", "pip", "install", "anthropic", "--quiet"],
        check=True
    )
    print("  ✓ anthropic installed")

    settings = load_settings()
    hook_cmd = f"{PYTHON} {HOOK_SCRIPT}"

    hook_entry = {
        "matcher": "",
        "hooks": [{"type": "command", "command": hook_cmd}]
    }

    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PreToolUse" not in settings["hooks"]:
        settings["hooks"]["PreToolUse"] = []

    # Remove any existing preflight entry
    settings["hooks"]["PreToolUse"] = [
        h for h in settings["hooks"]["PreToolUse"]
        if "preflight.py" not in str(h)
    ]

    settings["hooks"]["PreToolUse"].insert(0, hook_entry)
    save_settings(settings)

    print(f"  ✓ Hook registered in {SETTINGS_PATH}")
    print()
    print("Done! Preflight will fire on the next Claude Code session.")
    print()
    print("  Disable:   CLAUDEFF_PREFLIGHT=0  (env var)")
    print("  Uninstall: python install.py --uninstall")
    print()
    print("Manifests saved to: ~/.claude/preflight/")


def uninstall():
    print("Uninstalling claudeff preflight hook…")
    settings = load_settings()

    if "PreToolUse" in settings.get("hooks", {}):
        before = len(settings["hooks"]["PreToolUse"])
        settings["hooks"]["PreToolUse"] = [
            h for h in settings["hooks"]["PreToolUse"]
            if "preflight.py" not in str(h)
        ]
        removed = before - len(settings["hooks"]["PreToolUse"])
        if removed:
            save_settings(settings)
            print(f"  ✓ Removed {removed} hook entry(s) from {SETTINGS_PATH}")
        else:
            print("  Hook not found in settings — nothing to remove.")
    else:
        print("  No PreToolUse hooks in settings — nothing to remove.")

    print("Done.")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
