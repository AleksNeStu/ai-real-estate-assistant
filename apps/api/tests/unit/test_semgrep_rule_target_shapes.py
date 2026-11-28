"""
The rule has to fire in the shape the GUARD runs it in (Task #160).

Semgrep matches a rule's ``paths.include`` against the path RELATIVE TO THE
PROJECT ROOT, and the project root of a scan is the common ancestor of its
targets. For a FILE target that ancestor is the file's own directory, so the
path that is matched is the bare filename - and a rule scoped to
``apps/api/**`` can never match it.

Measured 2026-11-28 on this machine, with the scope as it stood:

- a file target, with or without ``--project-root``: the rule never fires;
- a directory target rooted at ``apps/api``: the rule never fires (the path
  that is matched is relative to ``apps/api``);
- a directory target with ``--project-root .``: the rule fires.

So the pre-push hook - which passes the changed FILES - never fired the rule,
and neither did the CI gate, which scans the directories it declares. The
guard the operator believes runs at push time did not run.

The rule's scope is therefore written so that it holds in EVERY shape: the
include matches any Python file, and the excludes name the tests by the names
pytest collects them under, so a test file is pruned whether the scan reaches
it as a directory or as a file.

The proof is deterministic: no LLM, no provider key, no network. The fixture is
a deliberate violation written into a scratch copy of the ruleset, and the
hook's own command - read out of ``.pre-commit-config.yaml``, not copied - is
run over it.
"""

import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SEMGREP = shutil.which("semgrep")
RULE_ID = "langchain.system-role-untrusted-data"

# The shape the rule has to catch: data at the system role.
FIXTURE_SOURCE = '''
from langchain_core.messages import SystemMessage


def _system_prompt(memory: str):
    """The shape the rule has to catch: data at the system role."""
    return SystemMessage(content=memory)
'''

# A test file that writes the bad shape ON PURPOSE - the fixture the rule
# needs, not a violation of it.
TEST_FILE_WITH_THE_BAD_SHAPE = "apps/api/tests/unit/test_context_manager.py"


def _hook() -> dict[str, str]:
    """
    The pre-push semgrep hook, read out of the repository's own config.

    The command is read, never copied: a hook that is re-pointed at a
    different shape is picked up by the tests below without touching them.
    """
    text = (REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if "id: semgrep-sast" in line)

    hook: dict[str, str] = {}
    for line in lines[start + 1 :]:
        if not line.strip():
            continue
        match = re.match(r"^ {8}(\w+):\s*(.*)$", line)
        if not match:
            break
        hook[match.group(1)] = match.group(2).strip().strip('"').strip("'")

    assert "entry" in hook, f"the semgrep hook has no entry: {hook}"
    return hook


def _command(targets: list[str], *extra: str) -> list[str]:
    """The hook's command, with the resolved semgrep binary and the targets."""
    hook = _hook()
    parts = shlex.split(hook["entry"], posix=True)
    assert parts and parts[0] == "semgrep", f"unexpected entry: {parts}"
    return [str(SEMGREP), *parts[1:], *extra, *targets]


def _tree_with_a_fixture(tmp_path: Path, relative_dir: str) -> Path:
    """A tree with the ruleset and one deliberate violation in it."""
    directory = tmp_path / relative_dir
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO_ROOT / "semgrep.yml", tmp_path / "semgrep.yml")
    (directory / "_fixture.py").write_text(FIXTURE_SOURCE, encoding="utf-8")
    return directory


def _run(cwd: Path, targets: list[str], *extra: str) -> subprocess.CompletedProcess:
    """Run the hook's own command over the targets."""
    return subprocess.run(
        _command(targets, *extra),
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _findings(cwd: Path, targets: list[str]) -> list[str]:
    """
    The rules that fired, in the same shape the hook runs.

    The hook's command is `--quiet`, so a finding prints nothing - it is the
    exit code that says so. The report is asked for as well, so the test can
    say WHICH rule fired.
    """
    result = _run(cwd, targets, "--json")
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    return [finding["check_id"] for finding in report.get("results", [])]


@pytest.mark.skipif(SEMGREP is None, reason="semgrep is not installed in this environment")
class TestTheRuleInEveryTargetShape:
    """The guard has to fire in the shape the guard runs in."""

    def test_the_pre_push_hook_fires_the_rule_on_a_changed_file(self, tmp_path):
        """The shape the pre-push hook uses: the changed files, as file targets."""
        _tree_with_a_fixture(tmp_path, "apps/api/ai")

        result = _run(tmp_path, ["apps/api/ai/_fixture.py"])

        assert result.returncode != 0, "the hook's own command did not fail on the fixture"
        assert RULE_ID in _findings(tmp_path, ["apps/api/ai/_fixture.py"]), (
            "the hook's own command did not flag the fixture with this rule"
        )

    def test_the_ci_gate_fires_the_rule_on_a_declared_directory(self, tmp_path):
        """The shape the CI gate uses: the directories it declares, as they are."""
        _tree_with_a_fixture(tmp_path, "apps/api/ai")
        targets = json.loads((REPO_ROOT / "quality-gate.json").read_text(encoding="utf-8"))["sast"][
            "targets"
        ]
        for target in targets:
            # The gate scans the directories it declares, so they have to be
            # there - a target that is missing is an error, not a finding.
            (tmp_path / target).mkdir(parents=True, exist_ok=True)

        result = _run(tmp_path, targets)

        assert result.returncode != 0, "the gate's own command did not fail on the fixture"
        assert RULE_ID in _findings(tmp_path, targets), (
            "the gate's own command did not flag the fixture with this rule"
        )

    def test_the_shipped_backend_is_not_flagged(self):
        """A push is not blocked by a finding that was already there."""
        backend = sorted(
            str(path.relative_to(REPO_ROOT).as_posix())
            for path in (REPO_ROOT / "apps" / "api").rglob("*.py")
            if "tests" not in path.parts and ".venv" not in str(path)
        )

        assert RULE_ID not in _findings(REPO_ROOT, backend), "the rule flagged the shipped backend"

    def test_a_test_that_writes_the_bad_shape_is_not_flagged(self):
        """
        The fixture the rule needs is not a violation of it.

        A test that builds a system message out of a variable on purpose is
        how the rule is proved - so it must be pruned, whether the scan
        reaches it as a file or as a directory.
        """
        assert RULE_ID not in _findings(REPO_ROOT, [TEST_FILE_WITH_THE_BAD_SHAPE]), (
            "the rule flagged a test that writes the bad shape"
        )
