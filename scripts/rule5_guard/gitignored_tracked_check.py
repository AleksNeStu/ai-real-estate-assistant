#!/usr/bin/env python3
"""
CI guard for Rule 5 in CLAUDE.md: gitignored files must NOT be tracked.

Verifies that the canonical list of gitignored local-only files is NOT in
the git index. Catches the regression where someone runs `git add -f .mcp.json`
(or any other force-add of a gitignored path) and leaks a local-only file
into the public, frozen repo history.

The check is intentionally scoped to the canonical list of paths Rule 5
explicitly protects. A broader "git ls-files -i -c --exclude-standard" check
would surface pre-existing drift in unrelated tracked-but-ignored files
(e.g. `docs/process/`, `docs/releases/`); cleaning that drift is a separate
out-of-scope task and not this guard's responsibility.

Canonical protected paths (see CLAUDE.md Rule 5):
  - .mcp.json                   (MCP server config, can contain secrets)
  - .env, .env.local            (environment files with secrets)
  - .env.ports, .env.*.local    (port allocation / local env overrides)

If the protected path is present on disk (untracked), it is NOT drift. If it
is present in the git index (tracked), the guard FAILS — that is the drift
pattern we are preventing.

Usage:
    python scripts/ci/gitignored_tracked_check.py
    python scripts/ci/gitignored_tracked_check.py --verbose
    python scripts/ci/gitignored_tracked_check.py --repo <path>

Exit codes:
    0: Pass - none of the canonical protected paths are tracked
    1: Fail - one or more canonical protected paths are tracked (must untrack
       before push; see CLAUDE.md Rule 5 remediation)
    2: Configuration error (not a git repo, missing tools, etc.)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Canonical protected paths per CLAUDE.md Rule 5. Edit with care — adding a
# path here is a policy change, not a code change.
PROTECTED_PATHS: tuple[str, ...] = (
    ".mcp.json",
    ".env",
    ".env.local",
    ".env.ports",
)


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command and return CompletedProcess with text output."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def check_repo(repo_root: Path) -> tuple[int, list[str]]:
    """
    Return (exit_code, tracked_protected_paths).

    exit_code:
      0 - clean (no canonical protected path is tracked)
      1 - drift detected
      2 - configuration error
    """
    if not (repo_root / ".git").exists():
        print(f"Error: not a git repository: {repo_root}", file=sys.stderr)
        return 2, []

    if shutil.which("git") is None:
        print("Error: 'git' executable not found in PATH", file=sys.stderr)
        return 2, []

    # `git ls-files --error-unmatch <path>` exits 0 if the path is in the
    # index, 1 otherwise. This is the canonical way to check "is this
    # specific path tracked?" without scanning the whole tree.
    drift: list[str] = []
    for relpath in PROTECTED_PATHS:
        result = _run_git(
            ["ls-files", "--error-unmatch", relpath],
            cwd=repo_root,
        )
        if result.returncode == 0:
            drift.append(relpath)
        elif result.returncode == 1:
            # Path is not tracked - this is the desired state.
            continue
        else:
            # Unexpected git error (e.g. internal error or signal).
            print(
                f"Error: git ls-files --error-unmatch {relpath} "
                f"failed (exit {result.returncode}): "
                f"{result.stderr.strip()}",
                file=sys.stderr,
            )
            return 2, []

    return (0 if not drift else 1), drift


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail CI if any canonical Rule 5 protected path "
            "(.mcp.json, .env, .env.local, .env.ports) is tracked in the "
            "git index."
        ),
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent,
        help="Path to the git repository root (default: repo root of this file).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print each protected path's checked state (tracked / untracked).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Rule 5 Guard: canonical gitignored paths must be untracked")
    print("=" * 60)
    print(f"Repository: {args.repo}")
    print("Protected paths (must be untracked):")
    for path in PROTECTED_PATHS:
        print(f"  - {path}")
    print()

    exit_code, drift = check_repo(args.repo)

    if args.verbose:
        for path in PROTECTED_PATHS:
            tracked = path in drift
            print(f"  [tracked={'YES' if tracked else 'no '}] {path}")
        print()

    if exit_code == 0:
        print("OK: none of the canonical Rule 5 paths are tracked.")
        print("    Invariant holds.")
        print("=" * 60)
        return 0

    if exit_code == 2:
        return 2

    # exit_code == 1 -> drift
    print("FAIL: the following canonical Rule 5 paths are TRACKED in git:")
    for path in drift:
        print(f"  - {path}")
    print()
    print("Remediation (per CLAUDE.md Rule 5):")
    print("  git rm --cached <path>          # untrack without deleting local file")
    print("  # Commit the untrack in a dedicated commit (do NOT mix with")
    print("  # feature work). Never `git add -f` a gitignored path.")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())