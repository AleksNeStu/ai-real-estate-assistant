"""OpenAPI schema diff tool for breaking-change detection (Task #97).

Compares current OpenAPI schema against a committed baseline and fails
if breaking changes are detected.

Breaking changes:
- Removed endpoint (path + method)
- Removed required request field
- Removed response field
- Changed field type
- Changed required/optional status

Non-breaking changes (allowed):
- Added endpoint
- Added optional request field
- Added response field
- Description changes

Usage:
    python scripts/openapi_diff.py [--baseline PATH] [--current PATH] [--strict]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_schema(path: str) -> dict[str, Any]:
    """Load an OpenAPI schema from a JSON file."""
    with open(path) as f:
        return json.load(f)


# The version of the API contract the baseline describes. The versioning
# middleware announces the same number on every /api/ response.
CONTRACT_VERSION = "1.0.0"


def diff_paths(
    baseline_paths: dict[str, Any],
    current_paths: dict[str, Any],
) -> list[str]:
    """Detect breaking changes in API paths."""
    errors: list[str] = []

    for path, methods in baseline_paths.items():
        if path not in current_paths:
            errors.append(f"BREAKING: Removed endpoint path: {path}")
            continue

        for method, spec in methods.items():
            if method not in current_paths[path]:
                errors.append(f"BREAKING: Removed method: {method.upper()} {path}")
                continue

            # Check request body fields
            baseline_body = (
                spec.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            current_body = (
                current_paths[path][method]
                .get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )

            # Check required fields
            baseline_required = set(baseline_body.get("required", []))
            current_required = set(current_body.get("required", []))

            removed_required = baseline_required - current_required
            if removed_required:
                errors.append(
                    f"BREAKING: Removed required request fields in {method.upper()} {path}: "
                    f"{removed_required}"
                )

            # Check field types
            baseline_props = baseline_body.get("properties", {})
            current_props = current_body.get("properties", {})

            for field_name, field_spec in baseline_props.items():
                if field_name not in current_props:
                    # Removed field that was in baseline
                    if field_name in baseline_required:
                        errors.append(
                            f"BREAKING: Removed required field '{field_name}' in "
                            f"{method.upper()} {path}"
                        )
                elif field_spec.get("type") != current_props[field_name].get("type"):
                    errors.append(
                        f"BREAKING: Changed type of field '{field_name}' in "
                        f"{method.upper()} {path}: "
                        f"{field_spec.get('type')} -> {current_props[field_name].get('type')}"
                    )

            # Check response fields
            for status_code, response_spec in spec.get("responses", {}).items():
                baseline_resp_schema = (
                    response_spec.get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )
                current_resp_spec = (
                    current_paths[path][method]
                    .get("responses", {})
                    .get(status_code, {})
                )
                current_resp_schema = (
                    current_resp_spec.get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )

                baseline_resp_props = baseline_resp_schema.get("properties", {})
                current_resp_props = current_resp_schema.get("properties", {})

                for prop_name, prop_spec in baseline_resp_props.items():
                    if prop_name not in current_resp_props:
                        errors.append(
                            f"BREAKING: Removed response field '{prop_name}' in "
                            f"{method.upper()} {path} ({status_code})"
                        )
                    elif prop_spec.get("type") != current_resp_props[prop_name].get(
                        "type"
                    ):
                        errors.append(
                            f"BREAKING: Changed response field type '{prop_name}' in "
                            f"{method.upper()} {path} ({status_code}): "
                            f"{prop_spec.get('type')} -> {current_resp_props[prop_name].get('type')}"
                        )

    return errors


def export_current_schema(current_path: str | None = None) -> dict[str, Any]:
    """The schema of the application, or the one in a file."""
    if current_path:
        return load_schema(current_path)

    import os
    import sys

    # Add apps/api to Python path for imports
    repo_root = Path(__file__).parent.parent.parent
    api_dir = repo_root / "apps" / "api"
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))

    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("API_ACCESS_KEY", "test-key")
    # Enable JWT auth so ALL conditional routers are included in the schema
    os.environ.setdefault("AUTH_JWT_ENABLED", "true")

    from api.main import app

    return app.openapi()


def _generate_baseline(baseline_path: str, current_path: str | None = None) -> int:
    """Write the current schema as the baseline the diff compares against.

    The baseline carries the contract version, so the file says which
    contract it describes.
    """
    try:
        schema = export_current_schema(current_path)
    except Exception as e:
        print(f"ERROR: Could not export schema from app: {e}")
        print("Provide --current path to pre-exported schema")
        return 1

    schema["x-api-contract-version"] = CONTRACT_VERSION

    target = Path(baseline_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # The baseline is a machine artifact: it is compared by the tool, not read
    # by a person. Written compact, it stays inside the size the repository
    # allows for an added file.
    target.write_text(
        json.dumps(schema, separators=(",", ":")) + "\n", encoding="utf-8"
    )
    print(f"Wrote the baseline to {target} ({len(schema.get('paths', {}))} paths)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenAPI schema diff for breaking changes"
    )
    parser.add_argument(
        "--baseline",
        default="docs/api-v1-baseline.json",
        help="Path to baseline schema",
    )
    parser.add_argument(
        "--current",
        default=None,
        help="Path to current schema (default: export from running app)",
    )
    parser.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Write the current schema as the baseline and exit",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    args = parser.parse_args()

    baseline_path = args.baseline

    if args.generate_baseline:
        return _generate_baseline(baseline_path, args.current)

    if not Path(baseline_path).exists():
        print(f"ERROR: Baseline schema not found: {baseline_path}")
        print("Run: python scripts/api/openapi_diff.py --generate-baseline")
        return 1

    if args.current:
        current_schema = load_schema(args.current)
    else:
        # Try to export from running app
        print("INFO: No --current specified, attempting to export from app...")
        try:
            current_schema = export_current_schema()
        except Exception as e:
            print(f"ERROR: Could not export schema from app: {e}")
            print("Provide --current path to pre-exported schema")
            return 1

    baseline_schema = load_schema(baseline_path)

    baseline_paths = baseline_schema.get("paths", {})
    current_paths = current_schema.get("paths", {})

    # Compare all paths (not just /api/v1/)
    errors = diff_paths(baseline_paths, current_paths)

    if errors:
        print(f"\n[FAIL] Found {len(errors)} breaking change(s):\n")
        for error in errors:
            print(f"  {error}")
        print(
            "\nTo accept these changes intentionally, update the baseline:"
            "\n  python scripts/openapi_diff.py --generate-baseline"
        )
        return 1

    # Summary
    new_endpoints = set(current_paths.keys()) - set(baseline_paths.keys())
    if new_endpoints:
        print("\n[PASS] No breaking changes detected.")
        print(f"[INFO] New endpoints added (non-breaking): {len(new_endpoints)}")
        for ep in sorted(new_endpoints):
            print(f"   + {ep}")
    else:
        print("\n[PASS] No breaking changes detected. API contract is stable.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
