"""Refresh the endpoint section of the API reference.

The reference document is written by hand — the explanations, the tables, the
warnings — but its endpoint list is generated from the OpenAPI schema, so it
cannot drift away from the endpoints the application actually serves.

The script rewrites the section that starts at `### Endpoints` and runs to
the next heading of the same level (or to the end of the document). Everything
before and after it is left alone.

Usage:
    python scripts/docs/update_api_reference_full.py            # rewrite the section
    python scripts/docs/update_api_reference_full.py --check    # fail if it drifted
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "apps" / "api"

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from api.openapi_markdown import (  # noqa: E402
    load_openapi_schema,
    serialize_endpoints_markdown,
)

DEFAULT_SCHEMA = REPO_ROOT / "docs" / "api" / "openapi.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "api" / "API_REFERENCE.md"

SECTION_HEADING = "### Endpoints"


def split_endpoints_section(document: str) -> tuple[str, str | None]:
    """Split the document into (before, section) at the endpoints heading.

    The section runs from the heading to the next heading of the same level.
    A document without the heading has no section.
    """
    lines = document.splitlines(keepends=True)

    start = None
    for index, line in enumerate(lines):
        if line.strip() == SECTION_HEADING:
            start = index
            break

    if start is None:
        return document, None

    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            end = index
            break

    return "".join(lines[:start]), "".join(lines[start:end])


def render(schema_path: Path, output_path: Path) -> str:
    """The document with a fresh endpoint section."""
    schema = load_openapi_schema(schema_path)
    endpoints = serialize_endpoints_markdown(schema)

    before, _ = split_endpoints_section(output_path.read_text(encoding="utf-8"))
    section = f"{SECTION_HEADING}\n\n{endpoints}"

    # The section is separated from the text above it by exactly one blank
    # line, whatever the text above it ends with.
    if not before.endswith("\n"):
        before += "\n"
    if before.strip() and not before.endswith("\n\n"):
        before += "\n"

    return before + section


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the endpoint section of the API reference",
    )
    parser.add_argument(
        "--schema", default=str(DEFAULT_SCHEMA), help="OpenAPI schema path"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT), help="Markdown file to update"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the committed file differs from the generated one",
    )
    args = parser.parse_args(argv)

    schema_path = Path(args.schema)
    output_path = Path(args.output)

    if not schema_path.exists():
        print(f"ERROR: schema not found: {schema_path}")
        return 1
    if not output_path.exists():
        print(f"ERROR: reference not found: {output_path}")
        return 1

    updated = render(schema_path, output_path)
    current = output_path.read_text(encoding="utf-8").replace("\r\n", "\n")

    if args.check:
        if current != updated:
            print("API reference drift detected. Regenerate with:")
            print("  python scripts/docs/update_api_reference_full.py")
            return 1
        print("API reference is up to date.")
        return 0

    output_path.write_text(updated, encoding="utf-8")
    print(f"Updated the endpoint section of {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
