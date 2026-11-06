"""Guards on the public repository's CI surface.

The deployment workflow and the platform blueprint were MOVED OUT of this public
repository on 2026-11-06 — TaskMaster #27, "serve the demo from our own server
behind a stable Cloudflare URL and hide the deployment topology from the public
repo". They now live in a private operations repository, next to the stack that
replaced them.

A public, frozen demo repository should not publish the service names, the
deploy-secret names, the platform API calls or the environment-variable recipe
of somebody's infrastructure. These tests pin THAT invariant, so the topology
cannot be reintroduced by accident.

The properties the deploy workflow itself has to keep — the owner guard, the
staging smoke gate, deploying the triggering SHA, serialising same-branch runs —
are pinned where the workflow now lives, in a private operations repository.
That location is deliberately not named here: naming it would publish the same
thing this file exists to keep out of the public tree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# The public repository must not name the hosting platform, a service
# identifier, a deploy secret, or a fleet node.
#
# The two platform-identifying needles are assembled from fragments on purpose:
# this file is part of the public tree, so it must not publish the very strings
# it forbids. (This file is excluded from its own scan for the same reason — it
# is the detector, not a leak.)
FORBIDDEN_IN_PUBLIC_TREE = (
    "on" + "render" + ".com",
    "dok" + "ploy",
    "render_api_key",
    "render_service_id",
    "render_backend_url",
    "render_frontend_url",
)


def _repo_root() -> Path:
    # Navigate from apps/api/tests/unit/ to repo root.
    return Path(__file__).resolve().parents[4]


def _workflow_path(name: str) -> Path:
    return _repo_root() / ".github" / "workflows" / name


def _tracked_files() -> list[Path]:
    """Every file git tracks — i.e. everything a visitor can see on GitHub.

    Deliberately NOT a filesystem walk: the working tree also holds local-only,
    gitignored files (a personal .env, the local MCP config, the operator's
    CLAUDE.md, editor settings, scratch directories). None of those are
    published, so none of them may fail this test.
    """
    root = _repo_root()
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    names = [n for n in result.stdout.decode("utf-8").split("\0") if n]
    return [root / name for name in names]


def _public_text_files() -> list[Path]:
    """The tracked files that are readable text, minus this test file.

    This file is excluded because it necessarily CONTAINS the forbidden
    strings — they are the needle list. It is the detector, not a leak.
    """
    this_file = Path(__file__).resolve()
    files: list[Path] = []
    for path in _tracked_files():
        if path.resolve() == this_file:
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        files.append(path)
    return files


def test_ci_workflow_has_no_mvp_disable_flag() -> None:
    workflow = _workflow_path("ci.yml")
    text = workflow.read_text(encoding="utf-8")

    assert "MVP_CI_DISABLED" not in text
    assert "env.MVP_CI_DISABLED" not in text
    assert "CI disabled notice" not in text


def test_public_repo_has_no_deploy_workflow() -> None:
    """The deploy pipeline is private now — it must not be reintroduced here."""
    assert not _workflow_path("deploy.yml").exists()
    assert not (_repo_root() / "render.yaml").exists()


def test_public_repo_workflow_set_is_the_expected_one() -> None:
    """Only the workflows a public demo needs stay in the public tree."""
    present = {path.name for path in (_repo_root() / ".github" / "workflows").glob("*.yml")}
    assert present == {
        "ci.yml",
        "dependabot-auto-merge.yml",
        "llm-costs.yml",
        "publish-ghcr.yml",
    }


def test_public_tree_names_no_infrastructure_identifier() -> None:
    """No hosting platform, service id, deploy secret or fleet node in public."""
    offenders: list[str] = []
    for path in _public_text_files():
        lowered = path.read_text(encoding="utf-8").lower()
        for needle in FORBIDDEN_IN_PUBLIC_TREE:
            if needle in lowered:
                offenders.append(f"{path.relative_to(_repo_root())}: {needle}")
    assert not offenders, "infrastructure identifiers leaked into the public tree:\n" + "\n".join(
        offenders
    )
