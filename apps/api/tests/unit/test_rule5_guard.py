"""
Unit tests for the Rule 5 guard (CLAUDE.md).

CLAUDE.md Rule 5 says canonical local-only paths (.mcp.json, .env,
.env.local, .env.ports) MUST stay out of the git index. If they ever
re-appear in the index — typically via `git add -f .mcp.json` or an
unguarded `git add -A` — this test fails, blocking the regression from
reaching public history.

The guard is implemented in scripts/ci/gitignored_tracked_check.py.
This test shells out to it and asserts the exit code is 0 (no drift).

This test runs in the backend `tests/unit` suite (per Rule 246 + Rule 128
local-CI parity). On failure, `make ci` and the GitHub Actions backend
job will both go red — the regression is caught automatically, not by a
human grep.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]  # apps/api/tests/unit/<file>.py -> 4 levels up to repo root
GUARD_SCRIPT = REPO_ROOT / "scripts" / "rule5_guard" / "gitignored_tracked_check.py"


@pytest.mark.skipif(
    shutil.which("git") is None, reason="git executable not available on PATH"
)
def test_rule5_protected_paths_are_not_tracked() -> None:
    """
    Invariant: CLAUDE.md Rule 5 protected paths are not tracked.

    If a developer force-stages .mcp.json (or any other canonical local-only
    path) the guard returns non-zero. This test fails when the guard fails,
    so the regression cannot reach `main`.
    """
    assert GUARD_SCRIPT.is_file(), (
        f"guard script missing at {GUARD_SCRIPT} — Rule 5 protection has been "
        "removed or relocated; restore the script before merging"
    )

    import subprocess

    result = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        "Rule 5 guard failed: one or more canonical gitignored paths are "
        "tracked in the git index. Remediation per CLAUDE.md:\n"
        "  git rm --cached <path>\n"
        "and commit the untrack in a dedicated commit.\n\n"
        f"guard stdout:\n{result.stdout}\n\n"
        f"guard stderr:\n{result.stderr}"
    )