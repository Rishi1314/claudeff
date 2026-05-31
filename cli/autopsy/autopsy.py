#!/usr/bin/env python3
"""
Bug autopsy — find which commits likely introduced a bug.

Usage:
    python autopsy.py "TypeError: cannot read property of undefined"
    python autopsy.py "login fails after token refresh" --top 10
    python autopsy.py "AttributeError" --repo /path/to/repo
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Terminal color helpers ─────────────────────────────────────────────────────

_COLORS = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLORS else text

def bold(t: str) -> str:   return _c("1", t)
def dim(t: str) -> str:    return _c("2", t)
def green(t: str) -> str:  return _c("32", t)
def yellow(t: str) -> str: return _c("33", t)
def cyan(t: str) -> str:   return _c("36", t)
def red(t: str) -> str:    return _c("31", t)

# ── Stop-words ─────────────────────────────────────────────────────────────────

_STOP = {
    "a","an","the","is","was","are","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might","shall","can",
    "to","of","in","for","on","with","at","by","from","up","about","into","through",
    "and","but","or","nor","so","yet","not","only","then","when","where","that",
    "this","these","those","who","which","what","how","why","also","just","very",
    "error","exception","line","file","cannot","undefined","null","none","true",
    "false","type","value","object","function","class","method","property",
    "attribute","module","import","return","call","called","calling","throws",
    "throw","raise","raises","raised","cause","caused","causes","fix","bug","issue",
    "problem","found","got","get","set","new","old","use","used","using","make",
    "made","run","ran","running","fail","fails","failed","failing","after","because",
}

# ── Data types ─────────────────────────────────────────────────────────────────

@dataclass
class Commit:
    hash: str
    short: str
    author: str
    date: datetime
    message: str
    files: list = field(default_factory=list)
    score: float = 0.0
    keywords: list = field(default_factory=list)

# ── Keyword extraction ─────────────────────────────────────────────────────────

def extract_keywords(desc: str) -> list:
    """Pull meaningful search tokens from a bug description."""
    # Expand camelCase
    expanded = re.sub(r'([a-z])([A-Z])', r'\1 \2', desc)
    # Split on punctuation / path separators
    expanded = re.sub(r'[_\-./:\\()\[\]{}"\']', ' ', expanded)

    tokens = re.findall(r'[A-Za-z][A-Za-z0-9]*', expanded)

    seen: set = set()
    result = []
    for t in tokens:
        key = t.lower()
        if key not in _STOP and len(t) >= 3 and t not in seen:
            seen.add(t)
            result.append(t)

    # Also preserve compound identifiers from the original (before expansion)
    for sym in re.findall(r'\b[A-Za-z_][A-Za-z0-9_]{2,}\b', desc):
        if sym not in seen and sym.lower() not in _STOP:
            seen.add(sym)
            result.append(sym)

    return result

# ── Git helpers ────────────────────────────────────────────────────────────────

def _run(args: list, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, capture_output=True, text=True, cwd=cwd,
        encoding="utf-8", errors="replace",
    )

def pickaxe(keyword: str, cwd: str, max_count: int = 40) -> list:
    """Return hashes of commits that added/removed a line containing keyword."""
    r = _run(["git", "log", "--all", "--format=%H", "-S", keyword,
              f"--max-count={max_count}"], cwd)
    if r.returncode != 0:
        return []
    return [h.strip() for h in r.stdout.splitlines() if h.strip()]

def commit_info(hash_: str, cwd: str) -> Optional[Commit]:
    """Fetch metadata for a single commit."""
    r = _run(["git", "log", "-1",
              "--format=%H%x00%h%x00%an%x00%aI%x00%s", hash_], cwd)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    parts = r.stdout.strip().split("\x00", 4)
    if len(parts) < 5:
        return None
    full, short, author, date_s, msg = parts
    try:
        date = datetime.fromisoformat(date_s.replace("Z", "+00:00"))
    except ValueError:
        date = datetime.now(timezone.utc)

    fr = _run(["git", "diff-tree", "--no-commit-id", "-r", "--name-only", hash_], cwd)
    files = [f.strip() for f in fr.stdout.splitlines() if f.strip()]

    return Commit(hash=full, short=short, author=author, date=date,
                  message=msg.strip(), files=files)

# ── Scoring ────────────────────────────────────────────────────────────────────

def score_commit(c: Commit, all_keywords: list, now: datetime) -> float:
    s = len(c.keywords) * 3.0           # each pickaxe hit is strong signal

    msg = c.message.lower()
    for kw in all_keywords:             # bonus for keywords in commit message
        if kw.lower() in msg:
            s += 1.5

    age_days = max(0, (now - c.date).days)
    s += max(0.0, 1.0 - age_days / 180.0) * 2.0   # recency bonus (decays over ~6 months)

    return s

# ── Report ─────────────────────────────────────────────────────────────────────

def _age(date: datetime, now: datetime) -> str:
    days = (now - date).days
    if days < 0:   return "in the future?"
    if days == 0:  return "today"
    if days == 1:  return "1 day ago"
    if days < 30:  return f"{days} days ago"
    if days < 365: return f"{days // 30} months ago"
    return f"{days // 365}y {(days % 365) // 30}m ago"

def print_report(commits: list, keywords: list, desc: str) -> None:
    W = 64
    sep  = dim("─" * W)
    dsep = bold("═" * W)

    print(dsep)
    print(bold("  BUG AUTOPSY"))
    print(dsep)
    print(f"  Query    : {desc}")
    print(f"  Keywords : {', '.join(keywords[:12])}"
          + (f"  (+{len(keywords)-12} more)" if len(keywords) > 12 else ""))
    print()

    if not commits:
        print(yellow("  No matching commits found."))
        print("  Tips:")
        print("    • Use symbol or function names from the stack trace")
        print("    • Try shorter, more specific fragments")
        print("    • Make sure --repo points to the right git repository")
        print(dsep)
        return

    now = datetime.now(timezone.utc)
    print(f"  {len(commits)} suspect commit(s) ranked by likelihood:\n")

    for i, c in enumerate(commits, 1):
        kw_str = ", ".join(c.keywords) if c.keywords else "(message match)"
        label_color = green if i == 1 else (yellow if i <= 3 else dim)

        print(sep)
        short_msg = c.message[:52] + ("…" if len(c.message) > 52 else "")
        print(f"  {bold(label_color(f'#{i}'))}  {bold(c.short)}  {short_msg}")
        print(f"      Author  : {c.author}  |  "
              f"{c.date.strftime('%Y-%m-%d')}  ({_age(c.date, now)})")
        print(f"      Score   : {c.score:.1f}  |  "
              f"keywords in code: {cyan(kw_str)}")
        if c.files:
            shown = c.files[:6]
            extra = len(c.files) - len(shown)
            print(f"      Changed : {', '.join(shown)}"
                  + (f"  … +{extra}" if extra else ""))
        print(f"      Inspect : {dim('git show ' + c.short)}")
        print()

    print(dsep)
    print(bold("  NEXT STEPS"))
    print(dsep)
    top = commits[0]
    print(f"  1. Inspect top suspect:")
    print(f"       git show {top.short}")
    print(f"  2. See surrounding commits:")
    print(f"       git log --oneline {top.short}~3..{top.short}")
    print(f"  3. Bisect to confirm:")
    print(f"       git bisect start")
    print(f"       git bisect bad HEAD")
    print(f"       git bisect good <last-known-good-ref>")
    print(dsep)

# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Bug autopsy — find commits that likely introduced a bug",
        epilog=(
            "examples:\n"
            "  python autopsy.py \"TypeError: cannot read property of undefined\"\n"
            "  python autopsy.py \"login fails after token refresh\" --top 10\n"
            "  python autopsy.py \"AttributeError: 'NoneType'\" --repo /other/repo"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("description", help="Bug description or error message")
    ap.add_argument("--top", type=int, default=5, metavar="N",
                    help="Show top N suspects (default: 5)")
    ap.add_argument("--repo", default=".", metavar="PATH",
                    help="Path to git repository (default: current directory)")
    args = ap.parse_args()

    repo = str(Path(args.repo).resolve())

    if _run(["git", "rev-parse", "--git-dir"], repo).returncode != 0:
        print(red(f"Error: '{repo}' is not a git repository"), file=sys.stderr)
        sys.exit(1)

    keywords = extract_keywords(args.description)
    if not keywords:
        print(red("Error: no searchable keywords found in description"), file=sys.stderr)
        sys.exit(1)

    search_kws = keywords[:12]  # cap to keep runtime bounded
    print(f"Searching {len(search_kws)} keyword(s): {', '.join(search_kws)}",
          file=sys.stderr)

    # Pickaxe search — one git log -S per keyword
    hash_kws: dict = defaultdict(list)
    for kw in search_kws:
        print(f"  git log -S {kw!r} ...                    ", file=sys.stderr, end="\r")
        for h in pickaxe(kw, repo):
            hash_kws[h].append(kw)

    total = len(hash_kws)
    print(f"  {total} unique candidate commit(s) found.        ", file=sys.stderr)

    if not hash_kws:
        print_report([], keywords, args.description)
        return

    # Sort by hit-count before fetching metadata — skip obvious noise
    sorted_hashes = sorted(hash_kws, key=lambda h: len(hash_kws[h]), reverse=True)

    now = datetime.now(timezone.utc)
    commits: list = []
    for h in sorted_hashes[:60]:       # cap metadata fetches to bound worst-case runtime
        c = commit_info(h, repo)
        if c:
            c.keywords = hash_kws[h]
            c.score    = score_commit(c, keywords, now)
            commits.append(c)

    commits.sort(key=lambda c: c.score, reverse=True)
    print_report(commits[: args.top], keywords, args.description)


if __name__ == "__main__":
    main()
