#!/usr/bin/env python3
"""Sort the NEXORA project board into Frontend Done / Backend Done / Both halves.

The rule (README, "Project board"): count a PR's added+deleted lines per side.

  frontend/  everything there except package.json, vite.config.js, vercel.json and
             eslint.config.js, which count for neither side
  backend/   everything there except tests
  neither    tests/, docs/, and root configuration

A card goes to Both halves when each side has at least 10 lines and the smaller side
is at least 15% of the larger. Otherwise it goes to the larger side, and a tie (or a
card with no code under either side: docs, config, tests) goes to Backend Done.

Three edge cases settle the way the board already is, and are spelled out here because
the rule on its own would misfile them:
  * frontend/package-lock.json counts as frontend. It is a frontend dependency change;
    the file is only excluded above for balance, not because it is not frontend work.
  * docs/frontend/** counts as frontend, at one line per file even when the file is a
    binary that reports no lines (the screenshots).
  * a side needs 10 lines to claim a card. A README PR that carries one CSS line is a
    docs PR, not frontend work.

Only PR cards already sitting in one of the three half columns are moved: that is the
sorting this script exists to do. A card in Backlog, In progress or rejected holds a
work state, not a half, and issue cards have no diff to read, so both are reported and
left alone.

    python scripts/sort_board.py              # show what would move, change nothing
    python scripts/sort_board.py --apply      # move the cards

Needs the GitHub CLI (`gh auth login` once). PR file stats are cached under the git
directory, so only new PRs are fetched after the first run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

OWNER = "SDF-FTH18M6-Capstones"
PROJECT_NUMBER = 9
PROJECT_ID = "PVT_kwDOFR5zZs4Bq1H7"
STATUS_FIELD_ID = "PVTSSF_lADOFR5zZs4Bq1H7zhpKcl8"
STATUS_OPTION = {
    "Frontend Done": "9247cc83",
    "Backend Done": "7a9405b9",
    "Both halves": "296765d5",
}
HALF_COLUMNS = tuple(STATUS_OPTION)

# Counting 10 lines minimum on a side, and 15% for a side to count as more than a trace.
MIN_LINES = 10
MIN_SHARE = 0.15

# Files under frontend/ that are configuration, not frontend work. The lockfile is not here:
# a dependency change is frontend work, it just cannot help judge balance.
FRONTEND_CONFIG = {
    "frontend/package.json",
    "frontend/vite.config.js",
    "frontend/vercel.json",
    "frontend/eslint.config.js",
}


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout


def repo_slug() -> str:
    return json.loads(gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]


def side_of(path: str) -> str:
    """Which half a changed file belongs to: 'fe', 'be' or 'neither'."""
    if path in FRONTEND_CONFIG:
        return "neither"
    if path.startswith("docs/frontend/"):
        return "fe"
    if path.startswith("frontend/"):
        return "fe"
    if path.startswith("tests/") or "/test_" in path or path.endswith("_test.py"):
        return "neither"
    if path.startswith("backend/"):
        return "be"
    return "neither"  # docs/, README, docker-compose.yml, pyproject.toml, render.yaml, ...


def weight(file_stats: dict) -> int:
    """Lines touched, with a file that reports none (a screenshot) still counting once."""
    return max(file_stats["additions"] + file_stats["deletions"], 1)


def classify(files: list[dict]) -> tuple[str, int, int]:
    totals = Counter()
    for file_stats in files:
        totals[side_of(file_stats["path"])] += weight(file_stats)

    frontend, backend = totals["fe"], totals["be"]
    smaller = min(frontend, backend)
    larger = max(frontend, backend)
    share = smaller / larger if larger else 0.0

    if frontend >= MIN_LINES and backend >= MIN_LINES and share >= MIN_SHARE:
        return "Both halves", frontend, backend
    if frontend > backend:
        return "Frontend Done", frontend, backend
    return "Backend Done", frontend, backend  # backend ahead, or a tie


def load_cache(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def fetch_pr_files(number: int, repo: str) -> list[dict]:
    """Every file a PR changed. `gh pr view --json files` stops at 100, which is not enough."""
    files, page = [], 1
    while page <= 40:
        batch = json.loads(
            gh("api", f"repos/{repo}/pulls/{number}/files?per_page=100&page={page}")
        )
        files.extend(
            {
                "path": item["filename"],
                "additions": item["additions"],
                "deletions": item["deletions"],
            }
            for item in batch
        )
        if len(batch) < 100:
            break
        page += 1
    return files


def pr_files(number: int, repo: str, cache: dict) -> list[dict]:
    key = str(number)
    if key not in cache:
        cache[key] = fetch_pr_files(number, repo)
    return cache[key]


def project_items() -> list[dict]:
    raw = gh(
        "project", "item-list", str(PROJECT_NUMBER), "--owner", OWNER,
        "--limit", "500", "--format", "json",
    )
    return json.loads(raw)["items"]


def move(item_id: str, column: str) -> None:
    gh(
        "project", "item-edit", "--id", item_id, "--project-id", PROJECT_ID,
        "--field-id", STATUS_FIELD_ID, "--single-select-option-id", STATUS_OPTION[column],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="File PR cards under the frontend/backend rule.")
    parser.add_argument("--apply", action="store_true", help="move the cards (default: dry run)")
    parser.add_argument("--all", action="store_true", help="also show cards the rule cannot place")
    args = parser.parse_args()

    repo = repo_slug()
    git_dir = Path(git("rev-parse", "--git-dir").strip() or ".git")
    cache_path = git_dir / "board-pr-cache.json"
    cache = load_cache(cache_path)

    items = project_items()
    moves, unchecked, skipped = [], [], []

    for item in items:
        number = (item.get("content") or {}).get("number")
        status = item.get("status")
        if status not in HALF_COLUMNS:
            skipped.append((status or "(no status)", item.get("title", ""), number))
            continue
        if number is None:
            continue
        if item.get("content", {}).get("type") != "PullRequest":
            unchecked.append(("issue", number, item.get("title", ""), status))
            continue
        column, frontend, backend = classify(pr_files(number, repo, cache))
        if column != status:
            moves.append((number, item["id"], status, column, frontend, backend, item.get("title", "")))

    cache_path.write_text(json.dumps(cache, indent=1, sort_keys=True), encoding="utf-8")

    total = sum(1 for item in items if item.get("status") in HALF_COLUMNS)
    print(f"{len(items)} cards on the board, {total} in the three half columns.")
    print(f"{len(moves)} would move.\n")

    if moves:
        print(f"{'PR':>6}  {'now':14} {'rule says':14} {'fe':>5} {'be':>5}  title")
        for number, _, now, want, frontend, backend, title in sorted(moves, key=lambda m: -m[4] - m[5]):
            print(f"#{number:<5}  {now:14} {want:14} {frontend:5} {backend:5}  {title[:52]}")

    if args.all and unchecked:
        print("\nIssue cards, which have no diff to read and stay where they are:")
        for _, number, title, status in unchecked:
            print(f"  [{status}] #{number} {title[:70]}")

    if args.all and skipped:
        print("\nCards outside the half columns, which hold a work state, not a half:")
        for status, title, number in skipped:
            print(f"  [{status}] #{number if number else '-'} {title[:70]}")

    if not args.apply:
        if moves:
            print("\nNothing changed. Re-run with --apply to move them.")
        return 0

    print()
    for number, item_id, now, want, *_ in moves:
        move(item_id, want)
        print(f"  #{number}: {now} -> {want}")
    print(f"\nMoved {len(moves)}.")
    if moves:
        print("Next: python scripts/sort_board.py   (it should now report 0 would move.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
