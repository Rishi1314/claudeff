#!/usr/bin/env python3
"""
allow_all.py — Add all common Claude Code tools to settings.json permissions.allow
so Claude never prompts for permission on standard operations.

Usage:
    python allow_all.py           # patch ~/.claude/settings.json
    python allow_all.py --undo    # remove the added permissions
    python allow_all.py --dry-run # preview without writing
"""

import argparse
import json
import sys
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

TOOLS = [
    "Bash",
    "Read",
    "Edit",
    "Write",
    "WebFetch",
    "Grep",
    "Glob",
    "LS",
    "MultiEdit",
    "NotebookRead",
    "NotebookEdit",
    "TodoRead",
    "TodoWrite",
    "WebSearch",
]


def load_settings(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_settings(path: Path, data: dict, dry_run: bool) -> None:
    text = json.dumps(data, indent=2)
    if dry_run:
        print(f"\nWould write to {path}:\n{text}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(text + "\n")


def apply(settings: dict) -> tuple[dict, list[str]]:
    allow: list = settings.setdefault("permissions", {}).setdefault("allow", [])
    added = [t for t in TOOLS if t not in allow]
    allow.extend(added)
    return settings, added


def undo(settings: dict) -> tuple[dict, list[str]]:
    allow: list = settings.get("permissions", {}).get("allow", [])
    removed = [t for t in TOOLS if t in allow]
    settings.setdefault("permissions", {})["allow"] = [t for t in allow if t not in TOOLS]
    return settings, removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--undo", action="store_true", help="Remove the added permissions")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--path", default=str(SETTINGS_PATH), help="Path to settings.json (default: ~/.claude/settings.json)")
    args = parser.parse_args()

    path = Path(args.path)
    settings = load_settings(path)

    if args.undo:
        settings, changed = undo(settings)
        verb, noun = "Removed", "permissions"
    else:
        settings, changed = apply(settings)
        verb, noun = "Added", "permissions"

    if not changed:
        print(f"Nothing to do — all {noun} already {'absent' if args.undo else 'present'}.")
        sys.exit(0)

    save_settings(path, settings, args.dry_run)

    label = " (dry run)" if args.dry_run else ""
    print(f"{verb} {len(changed)} {noun}{label}:")
    for t in changed:
        print(f"  + {t}" if not args.undo else f"  - {t}")
    if not args.dry_run:
        print(f"\nSaved to {path}")
        if not args.undo:
            print("Claude Code will no longer prompt for permission on these tools.")


if __name__ == "__main__":
    main()
