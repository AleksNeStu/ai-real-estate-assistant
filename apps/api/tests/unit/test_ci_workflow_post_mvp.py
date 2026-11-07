"""Guards on the public repository's CI surface.

The deployment workflow and the platform blueprint are part of this public
repository again (operator decision, 2026-11-07). A visitor who lands on the
repository should see a pipeline that actually deploys, and the demo keeps
deploying to its hosted services. What lives in the private operations
repository is the SECONDARY stack - the studio's own host - not this one.

So the deployment topology of THIS project is public on purpose. What stays
private is everything that is not the project's own deployment:

- no credential VALUE is ever committed (the workflow reads them from the
  repository secrets),
- no personal path from the machine that wrote the repository,
- no other infrastructure the studio runs (its nodes, its deployment tool).

These tests pin those invariants, so the pipeline can stay visible without the
tree becoming a map of somebody else's fleet.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# The deployment files that are public on purpose.
DEPLOY_WORKFLOW = ".github/workflows/deploy.yml"
DEPLOY_BLUEPRINT = "render.yaml"

# The second deployment target: a server the visitor owns.
SELFHOSTED_WORKFLOW = ".github/workflows/deploy-selfhosted.yml"
SELFHOSTED_COMPOSE = "deploy/docker-compose.selfhosted.yml"

# The CI workflow that gates the deploys.
CI_WORKFLOW = ".github/workflows/ci.yml"

# The workflows a public repository of this project carries.
EXPECTED_WORKFLOWS = {
    "ci.yml",
    "deploy.yml",
    "deploy-selfhosted.yml",
    "dependabot-auto-merge.yml",
    "llm-costs.yml",
    "publish-ghcr.yml",
}

# Names of the studio's own infrastructure. This repository deploys its own
# demo and must not describe anybody else's servers. The studio's own name is
# NOT in this list: the link to the studio is the project's lead channel and
# stays public on purpose.
FOREIGN_INFRASTRUCTURE = (
    "dok" + "ploy",
    "vps2",
    "vps3",
    "vps4",
    "vps5",
    "vps10",
)

# A path on the machine that wrote the repository.
PERSONAL_PATH = "C:" + "/Users/"

# Shapes of a credential value. The workflow must read these from the
# repository secrets, never carry them.
CREDENTIAL_VALUE_PATTERNS = (
    re.compile(r"rnd_[A-Za-z0-9]{10,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY"),
)

# Files that are generated or are themselves detectors, and therefore cannot
# be scanned for the patterns above without drowning in false positives.
SCAN_EXEMPT = {
    Path("apps/web/package-lock.json"),
    Path(".gitleaks.toml"),
    Path("apps/api/tests/unit/test_ci_workflow_post_mvp.py"),
}


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


def _relative(path: Path) -> Path:
    return path.relative_to(_repo_root())


def _public_text_files() -> list[Path]:
    """The tracked files that are readable text, minus the exempt ones."""
    files: list[Path] = []
    for path in _tracked_files():
        if _relative(path) in SCAN_EXEMPT:
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


def test_public_repo_has_the_deploy_pipeline() -> None:
    """The pipeline a visitor reads about must actually be in the tree."""
    assert _workflow_path("deploy.yml").exists()
    assert (_repo_root() / DEPLOY_BLUEPRINT).exists()


def test_public_repo_workflow_set_is_the_expected_one() -> None:
    """Exactly the workflows a public demo needs, and the deploy among them."""
    present = {path.name for path in (_repo_root() / ".github" / "workflows").glob("*.yml")}
    assert present == EXPECTED_WORKFLOWS


def test_deploy_workflow_keeps_its_guards() -> None:
    """The properties that make the pipeline safe to keep in a public repo.

    These were pinned in the private operations repository while the workflow
    lived there; they are pinned here now that it is public again.
    """
    text = _workflow_path("deploy.yml").read_text(encoding="utf-8")

    # It only runs for the owner of this repository.
    assert "github.repository_owner == 'AleksNeStu'" in text
    # It deploys only after the CI workflow has finished.
    assert "workflow_run:" in text
    assert 'workflows: ["CI/CD AI Real Estate Assistant"]' in text
    # It serialises same-branch deploys instead of cancelling them.
    assert "concurrency:" in text
    assert "cancel-in-progress: false" in text
    # Every credential it uses comes from the repository secrets.
    assert "secrets.RENDER_API_KEY" in text


def test_deploy_files_carry_no_credential_value() -> None:
    """The deploy pipeline reads its credentials; it never carries them."""
    for relative in (DEPLOY_WORKFLOW, DEPLOY_BLUEPRINT, SELFHOSTED_WORKFLOW, SELFHOSTED_COMPOSE):
        text = (_repo_root() / relative).read_text(encoding="utf-8")
        for pattern in CREDENTIAL_VALUE_PATTERNS:
            assert not pattern.search(text), f"{relative} carries a credential value"


def test_selfhosted_workflow_is_generic_and_guarded() -> None:
    """The second deployment target stays generic.

    A visitor may copy this workflow into their own fork and point it at
    their own server. That only works while the file names NO host, no user,
    no port and no path of its own - every one of them is a secret.
    """
    text = _workflow_path("deploy-selfhosted.yml").read_text(encoding="utf-8")

    # The stack a visitor copies to their server ships with this repository.
    assert (_repo_root() / SELFHOSTED_COMPOSE).exists()

    # Only the owner of this repository deploys.
    assert "github.repository_owner == 'AleksNeStu'" in text
    # And a repository without a target server deploys nothing. The check
    # cannot live in the job condition - GitHub does not expand a secret
    # there - so it is the first step of the job.
    assert "secrets.DEPLOY_HOST" in text
    assert "configured=false" in text
    # Every endpoint of the deployment comes from a secret.
    for secret in ("DEPLOY_HOST", "DEPLOY_USER", "DEPLOY_PORT", "DEPLOY_PATH"):
        assert f"secrets.{secret}" in text
    # The key is written to disk, not passed in the command line.
    assert "secrets.DEPLOY_SSH_KEY" in text
    # Serialised deploys, never cancelled half-way.
    assert "cancel-in-progress: false" in text
    # No address of any kind is written into the file.
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text), (
        "an IP address is written in the workflow"
    )
    assert "ssh-keyscan" in text


def test_public_tree_names_no_foreign_infrastructure() -> None:
    """This repository deploys its own demo and describes nobody else's fleet."""
    offenders: list[str] = []
    for path in _public_text_files():
        lowered = path.read_text(encoding="utf-8").lower()
        for needle in FOREIGN_INFRASTRUCTURE:
            if needle in lowered:
                offenders.append(f"{_relative(path)}: {needle}")
    assert not offenders, "foreign infrastructure named in the public tree:\n" + "\n".join(
        offenders
    )


def test_public_tree_carries_no_personal_path() -> None:
    """No path from the machine that wrote the repository is published."""
    offenders: list[str] = []
    for path in _public_text_files():
        if PERSONAL_PATH in path.read_text(encoding="utf-8"):
            offenders.append(str(_relative(path)))
    assert not offenders, "personal path in the public tree:\n" + "\n".join(offenders)
