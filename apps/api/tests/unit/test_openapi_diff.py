"""The public API contract is checked (Task #100).

A change to the public API is a change to a promise. The check compares the
schema the application serves with the baseline that was released, and it
fails on the differences a consumer cannot survive: a field that is gone, a
field that was renamed, a field whose type changed, a field that became
required. An additive change passes - a consumer that does not know the new
field ignores it.

The script is the one the pipeline runs, so the test drives the script
itself: the functions for the classification, and the command line for the
exit code and the message a consumer's author reads.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "scripts" / "api" / "openapi_diff.py"


def _load_script():
    """The script the pipeline runs, imported as a module."""
    spec = importlib.util.spec_from_file_location("openapi_diff", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    # The dataclasses in the script carry string annotations, and a dataclass
    # resolves them through the module it belongs to - so the module has to be
    # in sys.modules before it is executed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


openapi_diff = _load_script()


def _spec(properties: dict, required: list[str] | None = None) -> dict:
    """A one-endpoint API that returns a named object schema."""
    return {
        "openapi": "3.1.0",
        "info": {"title": "test", "version": "1.0.0"},
        "paths": {
            "/api/v1/things": {
                "get": {
                    "operationId": "list_things",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Thing"}
                                }
                            }
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "Thing": {
                    "type": "object",
                    "properties": properties,
                    "required": required or [],
                }
            }
        },
    }


def _breaking(baseline: dict, current: dict) -> list:
    """The changes a consumer cannot survive."""
    changes = openapi_diff.compare_specs(baseline, current)
    return [change for change in changes if change.severity == openapi_diff.BREAKING]


class TestTheBreakingChanges:
    """Each difference a consumer cannot survive is caught."""

    def test_a_removed_field_fails(self):
        baseline = _spec({"name": {"type": "string"}, "count": {"type": "integer"}})
        current = _spec({"name": {"type": "string"}})

        breaking = _breaking(baseline, current)

        assert len(breaking) == 1
        assert breaking[0].kind == "field-removed"
        # The message names the field the consumer reads.
        assert "count" in breaking[0].message
        assert "count" in breaking[0].field_path

    def test_a_renamed_field_fails(self):
        baseline = _spec({"name": {"type": "string"}, "count": {"type": "integer"}})
        current = _spec({"name": {"type": "string"}, "total": {"type": "integer"}})

        breaking = _breaking(baseline, current)

        assert [change.kind for change in breaking] == ["field-renamed"]
        assert "count" in breaking[0].message
        assert "total" in breaking[0].message

    def test_a_changed_type_fails(self):
        baseline = _spec({"name": {"type": "string"}})
        current = _spec({"name": {"type": "integer"}})

        breaking = _breaking(baseline, current)

        assert [change.kind for change in breaking] == ["type-changed"]
        assert "name" in breaking[0].message

    def test_a_newly_required_field_fails(self):
        baseline = _spec({"name": {"type": "string"}})
        current = _spec({"name": {"type": "string"}}, required=["name"])

        breaking = _breaking(baseline, current)

        assert [change.kind for change in breaking] == ["required-changed"]
        assert "name" in breaking[0].message

    def test_a_field_that_became_optional_fails(self):
        baseline = _spec({"name": {"type": "string"}}, required=["name"])
        current = _spec({"name": {"type": "string"}})

        breaking = _breaking(baseline, current)

        assert [change.kind for change in breaking] == ["required-changed"]


class TestTheCompatibleChanges:
    """A change a consumer can survive passes."""

    def test_an_added_optional_field_passes(self):
        baseline = _spec({"name": {"type": "string"}})
        current = _spec({"name": {"type": "string"}, "note": {"type": "string"}})

        assert _breaking(baseline, current) == []

    def test_an_added_endpoint_passes(self):
        baseline = _spec({"name": {"type": "string"}})
        current = _spec({"name": {"type": "string"}})
        current["paths"]["/api/v1/other"] = {
            "get": {"operationId": "list_other", "responses": {"200": {"content": {}}}}
        }

        assert _breaking(baseline, current) == []

    def test_an_identical_contract_has_no_changes(self):
        spec = _spec({"name": {"type": "string"}}, required=["name"])

        assert openapi_diff.compare_specs(spec, json.loads(json.dumps(spec))) == []


class TestTheCommandLine:
    """The command the pipeline runs: the exit code and the message."""

    def _run(self, baseline: dict, current: dict, tmp_path: Path, *extra: str):
        baseline_path = tmp_path / "baseline.json"
        current_path = tmp_path / "current.json"
        baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
        current_path.write_text(json.dumps(current), encoding="utf-8")

        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--baseline",
                str(baseline_path),
                "--current",
                str(current_path),
                *extra,
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

    def test_a_breaking_change_exits_non_zero_and_names_the_field(self, tmp_path):
        baseline = _spec({"name": {"type": "string"}, "count": {"type": "integer"}})
        current = _spec({"name": {"type": "string"}})

        result = self._run(baseline, current, tmp_path)

        assert result.returncode == 1
        assert "count" in result.stdout
        # The failure points at the command that accepts the change on purpose.
        assert "--update-baseline" in result.stdout

    def test_a_compatible_change_exits_zero(self, tmp_path):
        baseline = _spec({"name": {"type": "string"}})
        current = _spec({"name": {"type": "string"}, "note": {"type": "string"}})

        result = self._run(baseline, current, tmp_path)

        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_the_baseline_is_updated_by_a_command(self, tmp_path):
        current = _spec({"name": {"type": "string"}})
        current_path = tmp_path / "current.json"
        current_path.write_text(json.dumps(current), encoding="utf-8")
        baseline_path = tmp_path / "baseline.json"

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--baseline",
                str(baseline_path),
                "--current",
                str(current_path),
                "--update-baseline",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

        assert result.returncode == 0
        written = json.loads(baseline_path.read_text(encoding="utf-8"))
        assert written["components"]["schemas"]["Thing"]["properties"] == {
            "name": {"type": "string"}
        }

    def test_a_missing_baseline_is_a_failure_that_names_the_command(self, tmp_path):
        current = _spec({"name": {"type": "string"}})
        current_path = tmp_path / "current.json"
        current_path.write_text(json.dumps(current), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--baseline",
                str(tmp_path / "absent.json"),
                "--current",
                str(current_path),
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            check=False,
        )

        assert result.returncode == 1
        assert "--update-baseline" in result.stdout


if __name__ == "__main__":  # pragma: no cover - the script is the subject here
    pytest.main([__file__])
