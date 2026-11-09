"""Export the application's OpenAPI schema to the repository.

The snapshot in `docs/api/openapi.json` is what the API reference and the
breaking-change baseline are built from. A schema that is not exported after
a change drifts away from the endpoints the application really serves.

Usage:
    python scripts/docs/export_openapi.py           # write the snapshot
    python scripts/docs/export_openapi.py --check   # fail when it drifted
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "apps" / "api"

DEFAULT_OUTPUT = REPO_ROOT / "docs" / "api" / "openapi.json"


def export_schema() -> dict:
    """The schema of the running application."""
    if str(API_DIR) not in sys.path:
        sys.path.insert(0, str(API_DIR))

    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("API_ACCESS_KEY", "test-key")
    # The conditional routers are part of the contract, so the snapshot has to
    # carry them too.
    os.environ.setdefault("AUTH_JWT_ENABLED", "true")

    from api.main import app

    return app.openapi()


def _ordered(live: Any, template: Any) -> Any:
    """The live value, in the order the template carries it.

    The order of the keys inside a schema is the order the library that
    produced it chose, and it changes with the library version. Reordering a
    33 000-line snapshot for that reason is noise, not signal, so a
    regeneration keeps the order the committed file already uses wherever the
    two describe the same thing.
    """
    if isinstance(live, dict) and isinstance(template, dict):
        keys = [key for key in template if key in live]
        keys += [key for key in live if key not in template]
        return {key: _ordered(live[key], template.get(key)) for key in keys}

    if (
        isinstance(live, list)
        and isinstance(template, list)
        and len(live) == len(template)
    ):
        return [_ordered(item, template[index]) for index, item in enumerate(live)]

    return live


def serialize(schema: dict, template: dict | None = None) -> str:
    """The snapshot as the file carries it.

    The top-level keys are sorted, so the file starts the same way whatever
    the application builds the schema in; everything below them keeps the
    order the committed file already used, so a regeneration shows the
    endpoints that changed and nothing else.
    """
    ordered = _ordered(schema, template) if template else schema
    ordered = {key: ordered[key] for key in sorted(ordered)}
    return json.dumps(ordered, indent=2) + "\n"


def same_content(current: str, exported: str) -> bool:
    """Whether two snapshots carry the same schema.

    The comparison is on the parsed documents, not on the text: the order of
    the keys inside a schema is the order the library that produced it chose,
    and it changes with the library version. A reordering is not a drift of
    the contract; a changed endpoint or field is.
    """
    try:
        return json.loads(current) == json.loads(exported)
    except json.JSONDecodeError:
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the OpenAPI schema")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Snapshot path")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the committed snapshot differs from the exported one",
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output)

    try:
        schema = export_schema()
    except Exception as error:  # noqa: BLE001
        print(f"ERROR: could not export the schema: {error}")
        return 1

    template = None
    if output_path.exists():
        try:
            template = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            template = None

    exported = serialize(schema, template=template)

    if args.check:
        if not output_path.exists():
            print(f"ERROR: snapshot missing: {output_path}")
            return 1
        current = output_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if not same_content(current, exported):
            print("OpenAPI snapshot drift detected. Regenerate with:")
            print("  python scripts/docs/export_openapi.py")
            return 1
        print("The OpenAPI snapshot is up to date.")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(exported, encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
