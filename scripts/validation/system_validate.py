from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    details: str


def _run_check(results: list[CheckResult], name: str, fn) -> bool:
    try:
        ok, details = fn()
    except Exception as exc:
        ok = False
        details = f"exception: {exc}"
    results.append(CheckResult(name=name, ok=ok, details=details))
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate core backend functionality in-process."
    )
    parser.add_argument(
        "--environment", choices=["development", "production"], default="development"
    )
    ns = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = Path(__file__).resolve().parents[2]
    # Add both repo root and apps/api to Python path for monorepo structure
    api_dir = repo_root / "apps" / "api"
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    if str(api_dir) not in sys.path:
        sys.path.insert(0, str(api_dir))

    os.environ.setdefault("ENVIRONMENT", ns.environment)
    os.environ.setdefault("API_ACCESS_KEY", "ci-test-key")

    results: list[CheckResult] = []

    def validate_settings_guards():
        from config.settings import AppSettings

        try:
            AppSettings(environment="production", cors_allow_origins=["*"])
        except ValueError:
            return True, "production CORS wildcard rejected"
        return False, "expected production CORS wildcard rejection"

    def collect_route_paths(app) -> set[str]:
        """Every path the application serves, however FastAPI keeps it.

        FastAPI 0.163 no longer flattens an included router into app.routes:
        it keeps ONE object for it, and that object carries no `path` of its
        own. Reading `route.path` for every route therefore raised
        AttributeError on the pinned FastAPI, and this check - which no CI job
        runs - failed for anyone who installed the locked requirements. The
        included router's own routes live under `original_router`.
        """
        paths: set[str] = set()
        for route in app.routes:
            path = getattr(route, "path", None)
            if path:
                paths.add(path)
                continue
            original = getattr(route, "original_router", None)
            if original is None:
                continue
            paths.update(
                getattr(inner, "path")
                for inner in getattr(original, "routes", [])
                if getattr(inner, "path", None)
            )
        return paths

    def validate_app_routes():
        from api.main import app

        paths = collect_route_paths(app)
        required = {"/health", "/api/v1/verify-auth", "/openapi.json"}
        missing = sorted(required - paths)
        if missing:
            return False, f"missing routes: {missing}"
        return True, "core routes present"

    def validate_http_contract():
        from fastapi.testclient import TestClient

        from api.main import app

        client = TestClient(app)

        health = client.get("/health")
        if health.status_code != 200:
            return False, f"/health status={health.status_code}"
        if "X-Request-ID" not in health.headers:
            return False, "missing X-Request-ID header"

        no_key = client.get("/api/v1/verify-auth")
        if no_key.status_code != 401:
            return False, f"/api/v1/verify-auth without key status={no_key.status_code}"

        with_key = client.get(
            "/api/v1/verify-auth", headers={"X-API-Key": os.environ["API_ACCESS_KEY"]}
        )
        if with_key.status_code != 200:
            return False, f"/api/v1/verify-auth with key status={with_key.status_code}"
        payload = with_key.json()
        if payload.get("valid") is not True:
            return False, "verify-auth payload missing valid=true"

        openapi = client.get("/openapi.json")
        if openapi.status_code != 200:
            return False, f"/openapi.json status={openapi.status_code}"

        return True, "health/auth/openapi OK"

    ok = True
    ok &= _run_check(results, "Settings guards", validate_settings_guards)
    ok &= _run_check(results, "Routes present", validate_app_routes)
    ok &= _run_check(results, "HTTP contract", validate_http_contract)

    for r in results:
        status = "PASS" if r.ok else "FAIL"
        print(f"{status}: {r.name} - {r.details}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
