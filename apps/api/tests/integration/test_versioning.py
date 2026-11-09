"""Backward compatibility tests for API versioning contract (Task #97).

Validates:
- X-API-Version header on all /api/ responses
- OpenAPI baseline schema is valid and loadable
- Breaking-change detection works (removed fields, changed types, removed endpoints)
- Non-breaking changes are allowed (added endpoints, added optional fields)
- CI blocks on breaking changes
"""

import copy
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]  # apps/api/tests/integration → repo root
BASELINE_PATH = REPO_ROOT / "docs" / "api-v1-baseline.json"
OPENAPI_DIFF_SCRIPT = REPO_ROOT / "scripts" / "api" / "openapi_diff.py"


def _resolve_ref(schema: dict, root: dict) -> dict:
    """Resolve a $ref pointer inside the OpenAPI document."""
    if "$ref" not in schema:
        return schema
    ref_path = schema["$ref"]
    if not ref_path.startswith("#/"):
        return schema
    parts = ref_path[2:].split("/")
    node = root
    for part in parts:
        node = node[part]
    return node


def _resolve_refs_in_paths(paths: dict, root: dict) -> dict:
    """Return a deep copy of *paths* with requestBody/response $ref resolved."""
    resolved_paths: dict = {}
    for path, methods in paths.items():
        resolved_methods: dict = {}
        for method, spec in methods.items():
            spec = copy.deepcopy(spec)
            rb = spec.get("requestBody")
            if rb:
                for _ct, ct_val in rb.get("content", {}).items():
                    sch = ct_val.get("schema")
                    if sch and "$ref" in sch:
                        ct_val["schema"] = copy.deepcopy(_resolve_ref(sch, root))
            for _status, resp_spec in spec.get("responses", {}).items():
                for _ct, ct_val in resp_spec.get("content", {}).items():
                    sch = ct_val.get("schema")
                    if sch and "$ref" in sch:
                        ct_val["schema"] = copy.deepcopy(_resolve_ref(sch, root))
            resolved_methods[method] = spec
        resolved_paths[path] = resolved_methods
    return resolved_paths


@pytest.fixture()
def client():
    """Create a test client with auth overrides."""
    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("API_ACCESS_KEY", "test-key")

    from api.auth import get_api_key
    from api.main import app

    app.dependency_overrides[get_api_key] = lambda: "test-key"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def baseline_schema() -> dict:
    """Load the committed baseline schema."""
    assert BASELINE_PATH.exists(), f"Baseline schema not found: {BASELINE_PATH}"
    with open(BASELINE_PATH) as f:
        return json.load(f)


@pytest.fixture()
def resolved_paths(baseline_schema: dict) -> dict:
    """Baseline paths with $ref schemas resolved to inline schemas."""
    return _resolve_refs_in_paths(baseline_schema["paths"], baseline_schema)


# ---------------------------------------------------------------------------
# X-API-Version header tests
# ---------------------------------------------------------------------------


class TestAPIVersionHeader:
    """All /api/ responses must include X-API-Version header."""

    def test_api_v1_verify_auth_has_version_header(self, client):
        response = client.get("/api/v1/verify-auth")
        assert response.status_code == 200
        assert "x-api-version" in response.headers
        version = response.headers["x-api-version"]
        parts = version.split(".")
        assert len(parts) == 3, f"Version must be semver, got: {version}"

    def test_api_v1_search_has_version_header(self, client):
        response = client.post(
            "/api/v1/search",
            json={"query": "test"},
        )
        assert "x-api-version" in response.headers

    def test_api_v1_chat_has_version_header(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "hello"},
        )
        assert "x-api-version" in response.headers

    def test_non_api_path_no_version_header(self, client):
        """Paths outside /api/ should NOT have the version header."""
        response = client.get("/docs")
        if response.status_code == 200:
            assert "x-api-version" not in response.headers

    def test_version_header_format(self, client):
        response = client.get("/api/v1/verify-auth")
        version = response.headers.get("x-api-version", "")
        major, minor, patch = version.split(".")
        assert major.isdigit()
        assert minor.isdigit()
        assert patch.isdigit()


# ---------------------------------------------------------------------------
# Baseline schema validation
# ---------------------------------------------------------------------------


class TestBaselineSchema:
    """The committed baseline schema must be valid and complete."""

    def test_baseline_exists_and_valid_json(self, baseline_schema):
        assert isinstance(baseline_schema, dict)
        assert "paths" in baseline_schema
        assert isinstance(baseline_schema["paths"], dict)

    def test_baseline_has_required_v1_endpoints(self, baseline_schema):
        paths = baseline_schema["paths"]
        required = ["/api/v1/search", "/api/v1/chat", "/health"]
        for endpoint in required:
            assert endpoint in paths, f"Missing required endpoint: {endpoint}"

    def test_baseline_search_has_required_fields(self, baseline_schema):
        search = baseline_schema["paths"]["/api/v1/search"]["post"]
        body_schema = search["requestBody"]["content"]["application/json"]["schema"]
        # Resolve $ref if present
        body_schema = _resolve_ref(body_schema, baseline_schema)
        assert "query" in body_schema.get("required", [])
        props = body_schema["properties"]
        assert "query" in props
        assert props["query"]["type"] == "string"

    def test_baseline_chat_has_required_fields(self, baseline_schema):
        chat = baseline_schema["paths"]["/api/v1/chat"]["post"]
        body_schema = chat["requestBody"]["content"]["application/json"]["schema"]
        # Resolve $ref if present
        body_schema = _resolve_ref(body_schema, baseline_schema)
        assert "message" in body_schema.get("required", [])
        props = body_schema["properties"]
        assert "message" in props
        assert props["message"]["type"] == "string"

    def test_baseline_has_version_marker(self, baseline_schema):
        assert "x-api-contract-version" in baseline_schema
        assert baseline_schema["x-api-contract-version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Breaking-change detection (openapi_diff logic)
# ---------------------------------------------------------------------------


class TestBreakingChangeDetection:
    """Tests for the openapi_diff.py script logic."""

    def _diff(self, baseline_paths: dict, current_paths: dict) -> list[str]:
        """Run diff_paths from the openapi_diff module."""
        sys_path_backup = __import__("sys").path.copy()
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("openapi_diff", str(OPENAPI_DIFF_SCRIPT))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.diff_paths(baseline_paths, current_paths)
        finally:
            __import__("sys").path = sys_path_backup

    def test_removed_endpoint_detected(self, resolved_paths):
        baseline = resolved_paths
        current = {k: v for k, v in baseline.items() if k != "/health"}
        errors = self._diff(baseline, current)
        assert any("Removed endpoint" in e and "/health" in e for e in errors)

    def test_removed_method_detected(self, resolved_paths):
        baseline = resolved_paths
        current = {
            "/api/v1/search": {},  # POST method removed
            "/api/v1/chat": baseline["/api/v1/chat"],
            "/health": baseline["/health"],
        }
        errors = self._diff(baseline, current)
        assert any("Removed method" in e and "POST" in e for e in errors)

    def test_removed_required_field_detected(self, resolved_paths):
        baseline = resolved_paths
        current = json.loads(json.dumps(baseline))  # deep copy
        # Remove "query" from required
        search_body = current["/api/v1/search"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        search_body["required"] = []  # removed "query"
        errors = self._diff(baseline, current)
        assert any("Removed required request fields" in e for e in errors)

    def test_changed_field_type_detected(self, resolved_paths):
        baseline = resolved_paths
        current = json.loads(json.dumps(baseline))
        # Change "query" type from string to integer
        search_body = current["/api/v1/search"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        search_body["properties"]["query"]["type"] = "integer"
        errors = self._diff(baseline, current)
        assert any("Changed type" in e and "query" in e for e in errors)

    def test_removed_response_field_detected(self, resolved_paths):
        baseline = resolved_paths
        current = json.loads(json.dumps(baseline))
        # Remove "response" from chat 200 response
        chat_resp = current["/api/v1/chat"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        del chat_resp["properties"]["response"]
        errors = self._diff(baseline, current)
        assert any("Removed response field" in e and "response" in e for e in errors)

    def test_changed_response_field_type_detected(self, resolved_paths):
        baseline = resolved_paths
        current = json.loads(json.dumps(baseline))
        # Change "count" from integer to string
        search_resp = current["/api/v1/search"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        search_resp["properties"]["count"]["type"] = "string"
        errors = self._diff(baseline, current)
        assert any("Changed response field type" in e and "count" in e for e in errors)

    def test_no_breaking_changes_passes(self, resolved_paths):
        baseline = resolved_paths
        current = json.loads(json.dumps(baseline))
        errors = self._diff(baseline, current)
        assert errors == []

    def test_added_endpoint_is_non_breaking(self, resolved_paths):
        baseline = resolved_paths
        current = json.loads(json.dumps(baseline))
        # Add a new endpoint (non-breaking)
        current["/api/v1/reports"] = {
            "get": {
                "responses": {"200": {"description": "Reports"}},
            }
        }
        errors = self._diff(baseline, current)
        assert errors == []

    def test_added_optional_field_is_non_breaking(self, resolved_paths):
        baseline = resolved_paths
        current = json.loads(json.dumps(baseline))
        # Add optional field to search request
        search_body = current["/api/v1/search"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        search_body["properties"]["page_token"] = {"type": "string"}
        errors = self._diff(baseline, current)
        assert errors == []

    def test_added_response_field_is_non_breaking(self, resolved_paths):
        baseline = resolved_paths
        current = json.loads(json.dumps(baseline))
        # Add field to search response
        search_resp = current["/api/v1/search"]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        search_resp["properties"]["facets"] = {"type": "object"}
        errors = self._diff(baseline, current)
        assert errors == []
