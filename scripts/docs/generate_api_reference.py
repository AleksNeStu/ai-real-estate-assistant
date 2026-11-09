"""Generate the endpoint index of the API reference.

The document is written from the committed OpenAPI snapshot, so it lists the
endpoints the application serves and nothing else. The hand-written reference
(`docs/api/API_REFERENCE.md`) keeps its explanations; this file is the index.

Usage:
    python scripts/docs/generate_api_reference.py           # write the file
    python scripts/docs/generate_api_reference.py --check   # fail if it drifted
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "apps" / "api"

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from api.openapi_markdown import export_api_reference_markdown  # noqa: E402

DEFAULT_SCHEMA = REPO_ROOT / "docs" / "api" / "openapi.json"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "api" / "API_REFERENCE.generated.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the API endpoint index")
    parser.add_argument(
        "--schema", default=str(DEFAULT_SCHEMA), help="OpenAPI schema path"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT), help="Markdown file to write"
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
        print("Run: python scripts/docs/export_openapi.py")
        return 1

    try:
        export_api_reference_markdown(
            schema_path=schema_path,
            output_path=output_path,
            check=args.check,
        )
    except SystemExit as error:
        print(str(error))
        return 1

    print(f"The API endpoint index is up to date: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
