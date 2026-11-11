from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from typing import Callable


def _project_root() -> Path:
    """Get project root directory (2 levels up from scripts/docker/)."""
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SmokeConfig:
    compose_file: Path
    compose_override: Optional[Path]
    backend_health_url: str
    backend_verify_auth_url: str
    frontend_url: str
    api_access_key: str
    timeout_seconds: int
    interval_seconds: float
    build: bool
    down: bool
    dry_run: bool


def build_compose_base_command(
    compose_file: Path, compose_override: Path | None = None
) -> list[str]:
    cmd = ["docker", "compose", "-f", str(compose_file)]
    if compose_override is not None:
        # A workstation that hosts several stacks needs its own host ports;
        # the override is a local file that changes nothing inside the
        # compose network.
        cmd.extend(["-f", str(compose_override)])
    return cmd


def build_compose_up_command(base: list[str], *, build: bool) -> list[str]:
    cmd = [*base, "up", "-d"]
    if build:
        cmd.append("--build")
    return cmd


def build_compose_down_command(base: list[str]) -> list[str]:
    return [*base, "down", "--volumes", "--remove-orphans"]


def build_compose_ps_command(base: list[str]) -> list[str]:
    return [*base, "ps"]


def build_compose_logs_command(base: list[str]) -> list[str]:
    return [*base, "logs", "--no-color", "--tail", "200"]


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def run_diagnostics(base: list[str]) -> None:
    for cmd in (build_compose_ps_command(base), build_compose_logs_command(base)):
        try:
            run_command(cmd)
        except Exception:
            continue


def http_get_status(
    url: str, timeout_seconds: float, headers: dict[str, str] | None = None
) -> int:
    req = urllib.request.Request(url, method="GET", headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def wait_for_http_ok(
    url: str,
    *,
    timeout_seconds: int,
    interval_seconds: float,
    get_status: Callable[[str, float], int],
    sleep: Callable[[float], None],
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status: int | None = None
    while time.monotonic() < deadline:
        try:
            last_status = get_status(url, 2.0)
            if 200 <= last_status < 300:
                return
        except OSError:
            last_status = None
        sleep(interval_seconds)

    status_part = "unknown" if last_status is None else str(last_status)
    raise TimeoutError(f"Timed out waiting for {url} (last_status={status_part})")


def get_default_api_access_key_from_env() -> str:
    raw = os.environ.get("API_ACCESS_KEY", "").strip()
    if raw:
        return raw

    rotated = os.environ.get("API_ACCESS_KEYS", "")
    if not rotated:
        return ""
    first = next((v.strip() for v in rotated.split(",") if v.strip()), "")
    return first


def parse_args(argv: list[str]) -> SmokeConfig:
    parser = argparse.ArgumentParser(
        description="Docker Compose smoke test (backend + frontend)."
    )
    default_compose = _project_root() / "deploy" / "compose" / "docker-compose.yml"
    parser.add_argument("--compose-file", default=str(default_compose))
    parser.add_argument(
        "--compose-override",
        default="",
        help="A second compose file, applied over the first one (local host ports).",
    )
    parser.add_argument("--backend-health-url", default="http://localhost:8001/health")
    parser.add_argument(
        "--backend-verify-auth-url", default="http://localhost:8001/api/v1/verify-auth"
    )
    parser.add_argument("--frontend-url", default="http://localhost:3001/")
    parser.add_argument(
        "--api-access-key", default=get_default_api_access_key_from_env()
    )
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--down", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--ci", action="store_true", help="CI defaults: build+down, longer timeout."
    )

    ns = parser.parse_args(argv)
    build = bool(ns.build)
    down = bool(ns.down)
    timeout_seconds = int(ns.timeout_seconds)

    if ns.ci:
        build = True
        down = True
        timeout_seconds = max(timeout_seconds, 240)

    return SmokeConfig(
        compose_file=Path(ns.compose_file),
        compose_override=Path(ns.compose_override) if ns.compose_override else None,
        backend_health_url=str(ns.backend_health_url),
        backend_verify_auth_url=str(ns.backend_verify_auth_url),
        frontend_url=str(ns.frontend_url),
        api_access_key=str(ns.api_access_key),
        timeout_seconds=timeout_seconds,
        interval_seconds=float(ns.interval_seconds),
        build=build,
        down=down,
        dry_run=bool(ns.dry_run),
    )


def main(argv: list[str]) -> int:
    cfg = parse_args(argv)
    compose_file = cfg.compose_file.resolve()

    if not compose_file.exists():
        raise FileNotFoundError(f"Compose file not found: {compose_file}")

    override = cfg.compose_override
    if override is not None and not override.exists():
        raise FileNotFoundError(f"Compose override not found: {override}")
    base = build_compose_base_command(compose_file, override)
    up_cmd = build_compose_up_command(base, build=cfg.build)
    down_cmd = build_compose_down_command(base)

    if cfg.dry_run:
        print("UP:", " ".join(up_cmd))
        print("DOWN:", " ".join(down_cmd))
        print("CHECK:", cfg.backend_health_url)
        print("CHECK:", cfg.frontend_url)
        if cfg.api_access_key:
            print("CHECK_AUTH:", cfg.backend_verify_auth_url)
        else:
            print("CHECK_AUTH: (skipped; API_ACCESS_KEY/API_ACCESS_KEYS not set)")
        return 0

    try:
        run_command(up_cmd)
        try:
            wait_for_http_ok(
                cfg.backend_health_url,
                timeout_seconds=cfg.timeout_seconds,
                interval_seconds=cfg.interval_seconds,
                get_status=http_get_status,
                sleep=time.sleep,
            )
            wait_for_http_ok(
                cfg.frontend_url,
                timeout_seconds=cfg.timeout_seconds,
                interval_seconds=cfg.interval_seconds,
                get_status=http_get_status,
                sleep=time.sleep,
            )
            if cfg.api_access_key:
                wait_for_http_ok(
                    cfg.backend_verify_auth_url,
                    timeout_seconds=cfg.timeout_seconds,
                    interval_seconds=cfg.interval_seconds,
                    get_status=lambda url, timeout: http_get_status(
                        url, timeout, headers={"X-API-Key": cfg.api_access_key}
                    ),
                    sleep=time.sleep,
                )
        except Exception:
            run_diagnostics(base)
            raise
        return 0
    finally:
        if cfg.down:
            run_command(down_cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
