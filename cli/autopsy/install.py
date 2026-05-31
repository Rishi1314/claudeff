#!/usr/bin/env python3
"""
Bug autopsy installer.

Verifies prerequisites and prints usage.
No settings changes required — autopsy.py runs standalone.
"""

import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCRIPT = Path(__file__).parent / "autopsy.py"


def check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "OK" if ok else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{mark}] {label}{suffix}")
    return ok


def main() -> None:
    print("\nBug autopsy — checking prerequisites\n")

    py_ok = check(
        "Python 3.8+",
        sys.version_info >= (3, 8),
        f"found {sys.version.split()[0]}",
    )

    git_path = shutil.which("git")
    git_ok = check("git in PATH", git_path is not None,
                   git_path or "not found")

    script_ok = check("autopsy.py present", SCRIPT.exists(), str(SCRIPT))

    if not all([py_ok, git_ok, script_ok]):
        print("\n  Fix the issues above, then re-run.\n")
        sys.exit(1)

    print(f"\n  Ready.\n")
    print("  Usage:")
    print(f'    python "{SCRIPT}" "TypeError: cannot read property of undefined"')
    print(f'    python "{SCRIPT}" "login fails after token refresh" --top 10')
    print(f'    python "{SCRIPT}" "AttributeError" --repo /path/to/repo\n')


if __name__ == "__main__":
    main()
