from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from api.main import app as fastapi_app
from api.openapi_export import export_openapi_schema
from api.openapi_markdown import serialize_api_reference_markdown

REPO_ROOT = Path(__file__).resolve().parents[5]  # apps/api/tests/integration/api -> repo root


def test_generated_api_reference_contains_core_routes(tmp_path: Path) -> None:
    out = tmp_path / "openapi.json"
    export_openapi_schema(app=fastapi_app, output_path=out, check=False)

    schema = json.loads(out.read_text(encoding="utf-8"))
    md = serialize_api_reference_markdown(schema)

    assert "## GET /health" in md
    assert "## POST /api/v1/search" in md
    assert "## POST /api/v1/chat" in md


def test_the_committed_reference_is_current() -> None:
    """The endpoint list in the reference is written from the schema.

    A reference that lists an endpoint the application does not serve - or
    misses one it does - is a document that lies about the API. The generator
    writes the section from the schema, so the check is the generator's own
    comparison against the committed file.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "docs" / "update_api_reference_full.py"),
            "--check",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=300,
    )

    assert result.returncode == 0, (
        "The API reference has drifted away from the schema.\n"
        f"{result.stdout}\n{result.stderr}\n"
        "Refresh it with:\n"
        "  python scripts/docs/export_openapi.py && "
        "python scripts/docs/update_api_reference_full.py"
    )


def test_the_committed_endpoint_index_is_current() -> None:
    """The generated index lists the endpoints the application serves."""
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "docs" / "generate_api_reference.py"),
            "--check",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=300,
    )

    assert result.returncode == 0, (
        "The endpoint index has drifted away from the schema.\n"
        f"{result.stdout}\n{result.stderr}\n"
        "Refresh it with:\n"
        "  python scripts/docs/generate_api_reference.py"
    )
