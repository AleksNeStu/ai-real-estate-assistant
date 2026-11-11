from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class StepResult:
    name: str
    status: str
    duration_seconds: float
    details: str


def _truthy_env(name: str) -> bool:
    value = os.environ.get(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    log_file: Path | None = None,
) -> int:
    import platform

    # On Windows, use shell=True for external executables to resolve PATH issues
    # Python module invocations (sys.executable -m) work fine without shell
    use_shell = False
    if platform.system() == "Windows" and cmd:
        # Use shell for external commands (npm, docker, trivy, etc.)
        # but not for Python module invocations
        exe = cmd[0].lower() if cmd[0] else ""
        use_shell = not (
            exe.endswith(".exe")
            or exe.endswith("python")
            or exe.endswith("python3")
            or "python" in Path(exe).parts
            or (len(cmd) > 1 and cmd[0].endswith(sys.executable))
        )

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("wb") as fh:
            return int(
                subprocess.run(
                    cmd,
                    cwd=str(cwd) if cwd else None,
                    env=env,
                    stdout=fh,
                    stderr=fh,
                    shell=use_shell,  # nosec B602: commands are trusted/hardcoded in CI
                ).returncode
            )
    return int(
        subprocess.run(  # nosec B602: commands are trusted/hardcoded in CI
            cmd, cwd=str(cwd) if cwd else None, env=env, shell=use_shell
        ).returncode
    )


def _ensure_repo_root() -> Path:
    root = Path(__file__).resolve().parents[2]
    if not (root / "scripts" / "ci" / "ci_parity.py").exists():
        raise FileNotFoundError(
            "Expected to run from repository root (scripts/ci/ci_parity.py missing)."
        )
    return root


def _http_get(url: str, *, timeout_seconds: float) -> int:
    req = Request(url, method="GET")
    with urlopen(req, timeout=timeout_seconds) as resp:
        return int(resp.status)


def _wait_for_http_200(url: str, *, timeout_seconds: float) -> bool:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            return _http_get(url, timeout_seconds=2.0) == 200
        except URLError:
            time.sleep(0.25)
        except TimeoutError:
            time.sleep(0.25)
    return False


def _is_tool_available(cmd: list[str]) -> bool:
    try:
        return (
            subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ).returncode
            == 0
        )
    except OSError:
        return False


def _run_step(results: list[StepResult], name: str, fn) -> bool:
    print(f"Running {name}...", end="", flush=True)
    started = time.time()
    try:
        status, details = fn()
    except Exception as exc:
        status = "failed"
        details = f"exception: {exc}"
    duration = time.time() - started
    results.append(
        StepResult(name=name, status=status, duration_seconds=duration, details=details)
    )
    print(f" {status.upper()} ({duration:.1f}s)")
    return status in {"passed", "skipped"}


def _write_validation_report(
    root: Path, results: list[StepResult], *, mode: str
) -> Path:
    artifacts_dir = root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifacts_dir / "validation_report.md"

    lines: list[str] = []
    lines.append("# Validation Report")
    lines.append("")
    lines.append(f"- Mode: {mode}")
    lines.append(f"- Date: {time.strftime('%d.%m.%Y')}")
    lines.append("")
    lines.append("## Results")
    lines.append("")
    for r in results:
        lines.append(
            f"- {r.status.upper()}: {r.name} ({r.duration_seconds:.2f}s) - {r.details}"
        )
    lines.append("")
    lines.append("## Manual Verification Checklist")
    lines.append("")
    lines.append(
        "- Verify UI loads (local: http://localhost:3000, staging/prod: your FRONTEND_URL)"
    )
    lines.append(
        '- Run a sample search query like "apartments in Krakow" and confirm results render'
    )
    lines.append(
        "- Open Assistant and confirm streaming responses render progressively"
    )
    lines.append(
        "- Verify auth endpoint responds: GET /api/v1/verify-auth (requires X-API-Key)"
    )
    lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def _bench_health(url: str, *, samples: int = 5) -> tuple[bool, str]:
    durations: list[float] = []
    for _ in range(samples):
        started = time.time()
        try:
            status = _http_get(url, timeout_seconds=3.0)
        except Exception as exc:
            return False, f"failed ({exc})"
        if status != 200:
            return False, f"status={status}"
        durations.append(time.time() - started)
    p50 = sorted(durations)[len(durations) // 2]
    p95 = sorted(durations)[max(0, int(len(durations) * 0.95) - 1)]
    ok = p95 < 2.0
    return ok, f"p50={p50:.3f}s p95={p95:.3f}s"


def main(argv: list[str] | None = None) -> int:
    root = _ensure_repo_root()
    logs_dir = root / "artifacts" / "logs"

    parser = argparse.ArgumentParser(
        description="Run the full CI validation suite locally."
    )
    parser.add_argument(
        "--mode", choices=["local", "staging", "production"], default="local"
    )
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--backend-url", default=os.environ.get("BACKEND_URL"))
    parser.add_argument("--frontend-url", default=os.environ.get("FRONTEND_URL"))
    parser.add_argument("--api-key", default=os.environ.get("API_ACCESS_KEY"))
    parser.add_argument("--skip-compose", action="store_true")
    parser.add_argument("--skip-frontend", action="store_true")
    parser.add_argument("--skip-e2e", action="store_true")
    parser.add_argument("--skip-security", action="store_true")
    parser.add_argument("--skip-trivy", action="store_true")
    parser.add_argument("--skip-bench", action="store_true")
    parser.add_argument(
        "--use-docker-frontend",
        action="store_true",
        help="Run frontend CI in Docker container",
    )
    ns = parser.parse_args(list(argv) if argv is not None else None)

    results: list[StepResult] = []
    exit_code = 1

    def backend_ci():
        log_file = logs_dir / "backend_ci_parity.log"
        cmd = [sys.executable, "scripts/ci/ci_parity.py"]
        if ns.base_ref:
            cmd.extend(["--base-ref", str(ns.base_ref)])
        rc = _run(cmd, cwd=root, log_file=log_file)
        return ("passed" if rc == 0 else "failed", f"log={log_file.as_posix()}")

    def frontend_ci():
        if ns.skip_frontend:
            return "skipped", "--skip-frontend"

        log_file = logs_dir / "frontend_ci.log"

        # Use Docker if requested (to avoid Windows file locking issues)
        if ns.use_docker_frontend:
            if not _is_tool_available(["docker", "--version"]):
                return "skipped", "docker not available"
            # Run frontend CI in Docker container
            rc1 = _run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{root}:/app",
                    "-w",
                    "/app/frontend",
                    "node:20-alpine",
                    "sh",
                    "-c",
                    "npm ci && npm run lint && npm run test -- --ci --coverage",
                ],
                cwd=root,
                log_file=log_file,
            )
            return (
                "passed" if rc1 == 0 else "failed",
                f"log={log_file.as_posix()} (Docker)",
            )

        # Original implementation for non-Docker mode (monorepo: apps/web)
        #
        # `npm ci` on Windows fails with EBUSY when a running next/jest still
        # holds the native .node binary open - a lock, not a broken
        # dependency tree. One retry after a pause clears it; the Docker mode
        # above has no locks at all.
        rc1 = _run(["npm", "--prefix", "apps/web", "ci"], cwd=root, log_file=log_file)
        if rc1 != 0:
            time.sleep(15)
            rc1 = _run(["npm", "--prefix", "apps/web", "ci"], cwd=root, log_file=log_file)
        used_fallback = False
        if rc1 != 0:
            rc1_fallback = _run(
                ["npm", "--prefix", "apps/web", "install", "--no-audit", "--no-fund"],
                cwd=root,
                log_file=log_file,
            )
            if rc1_fallback != 0:
                return "failed", f"log={log_file.as_posix()}"
            used_fallback = True
        rc2 = _run(
            ["npm", "--prefix", "apps/web", "run", "lint"], cwd=root, log_file=log_file
        )
        if rc2 != 0:
            return "failed", f"log={log_file.as_posix()}"
        rc3 = _run(
            ["npm", "--prefix", "apps/web", "run", "test", "--", "--ci", "--coverage"],
            cwd=root,
            log_file=log_file,
        )
        status = "passed" if rc3 == 0 else "failed"
        details = f"log={log_file.as_posix()}"
        if used_fallback:
            details += " (npm install fallback used)"
        return (status, details)

    def compose_smoke():
        if ns.skip_compose:
            return "skipped", "--skip-compose"
        # Check if Docker daemon is actually running, not just CLI installed
        if not _is_tool_available(["docker", "info"]):
            return "skipped", "docker daemon not running"
        log_file = logs_dir / "compose_smoke.log"
        # The smoke script lives under scripts/docker/ - that is where the
        # Makefile's smoke-test target and the CI workflow call it from
        # (scripts/ci/compose_smoke.py does not exist, so the step failed with
        # "can't open file"). The timeout matches the workflow's.
        cmd = [
            sys.executable,
            "scripts/docker/compose_smoke.py",
            "--ci",
            "--timeout-seconds",
            "600",
        ]
        # A workstation that hosts several stacks needs its own host ports;
        # the override is named by the environment and changes nothing inside
        # the compose network.
        override = os.environ.get("AIRE_COMPOSE_OVERRIDE", "").strip()
        if override:
            cmd.extend(["--compose-override", override])
            # The override publishes the stack on other host ports, so the
            # checks follow it.
            backend_url = os.environ.get("AIRE_SMOKE_BACKEND_URL", "").strip()
            frontend_url = os.environ.get("AIRE_SMOKE_FRONTEND_URL", "").strip()
            if backend_url:
                cmd.extend(["--backend-health-url", backend_url])
            if frontend_url:
                cmd.extend(["--frontend-url", frontend_url])
        rc = _run(
            cmd,
            cwd=root,
            log_file=log_file,
        )
        return ("passed" if rc == 0 else "failed", f"log={log_file.as_posix()}")

    def security_scans():
        if ns.skip_security:
            return "skipped", "--skip-security"
        return "passed", "included in Backend CI parity"

    def taskmaster_validate():
        log_file = logs_dir / "taskmaster_validate.log"
        rc = _run(
            [sys.executable, "scripts/validation/validate_taskmaster.py"],
            cwd=root,
            log_file=log_file,
        )
        return ("passed" if rc == 0 else "failed", f"log={log_file.as_posix()}")

    def system_validate():
        if ns.mode != "local":
            return "skipped", f"mode={ns.mode}"
        log_file = logs_dir / "system_validate.log"
        rc = _run(
            [
                sys.executable,
                "scripts/validation/system_validate.py",
                "--environment",
                "development",
            ],
            cwd=root,
            log_file=log_file,
        )
        return ("passed" if rc == 0 else "failed", f"log={log_file.as_posix()}")

    def remote_smoke():
        if ns.mode == "local":
            return "skipped", "mode=local"
        if not ns.backend_url:
            return "skipped", "BACKEND_URL not set"
        health_url = ns.backend_url.rstrip("/") + "/health"
        try:
            status = _http_get(health_url, timeout_seconds=5.0)
        except Exception as exc:
            return "failed", f"GET {health_url} failed ({exc})"
        if status != 200:
            return "failed", f"GET {health_url} status={status}"
        if ns.api_key:
            verify_url = ns.backend_url.rstrip("/") + "/api/v1/verify-auth"
            req = Request(
                verify_url, method="GET", headers={"X-API-Key": str(ns.api_key)}
            )
            try:
                with urlopen(req, timeout=5.0) as resp:
                    auth_status = int(resp.status)
            except Exception as exc:
                return "failed", f"GET {verify_url} failed ({exc})"
            if auth_status != 200:
                return "failed", f"GET {verify_url} status={auth_status}"
        return "passed", f"backend={ns.backend_url}"

    def e2e_tests():
        if ns.skip_e2e:
            return "skipped", "--skip-e2e"
        if ns.mode != "local":
            return "skipped", f"mode={ns.mode}"
        # Skip E2E tests on Windows due to FastEmbed/Vector store being disabled
        import platform

        if platform.system() == "Windows":
            return (
                "skipped",
                "Windows: FastEmbed disabled, E2E tests require vector store",
            )

        uvicorn_log = logs_dir / "e2e_backend_uvicorn.log"
        uvicorn_log.parent.mkdir(parents=True, exist_ok=True)
        uvicorn_fh = uvicorn_log.open("wb")
        backend_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=str(root),
            env={
                **os.environ,
                "ENVIRONMENT": "development",
                "API_ACCESS_KEY": os.environ.get("API_ACCESS_KEY", "ci-test-key"),
            },
            stdout=uvicorn_fh,
            stderr=subprocess.STDOUT,
        )
        try:
            if not _wait_for_http_200(
                "http://127.0.0.1:8000/health", timeout_seconds=30.0
            ):
                return "failed", f"log={uvicorn_log.as_posix()}"

            npm_log = logs_dir / "e2e_root_npm_ci.log"
            rc_root = _run(["npm", "ci"], cwd=root, log_file=npm_log)
            if rc_root != 0:
                rc_root_fallback = _run(
                    ["npm", "install", "--no-audit", "--no-fund"],
                    cwd=root,
                    log_file=npm_log,
                )
                if rc_root_fallback != 0:
                    return "failed", f"log={npm_log.as_posix()}"

            env = {
                **os.environ,
                "PLAYWRIGHT_START_WEB": "1",
                "BACKEND_API_URL": "http://127.0.0.1:8000",
                "API_ACCESS_KEY": os.environ.get("API_ACCESS_KEY", "ci-test-key"),
            }
            pw_log = logs_dir / "playwright_e2e.log"
            rc = _run(["npm", "run", "test:e2e"], cwd=root, env=env, log_file=pw_log)
            return ("passed" if rc == 0 else "failed", f"log={pw_log.as_posix()}")
        finally:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend_proc.kill()
            uvicorn_fh.close()

    def trivy_scan():
        if ns.skip_trivy:
            return "skipped", "--skip-trivy"
        if not _is_tool_available(["trivy", "--version"]):
            return "skipped", "trivy not installed"
        if not _is_tool_available(["docker", "--version"]):
            return "skipped", "docker not available"
        log_file = logs_dir / "trivy_scan.log"
        # Build backend (monorepo: apps/api)
        rc1 = _run(
            [
                "docker",
                "build",
                "-f",
                "deploy/docker/Dockerfile.backend",
                "-t",
                "ai-backend:ci",
                ".",
            ],
            cwd=root,
            log_file=log_file,
        )
        if rc1 != 0:
            return "failed", f"log={log_file.as_posix()}"
        # Build frontend (deploy/docker/Dockerfile.frontend)
        rc2 = _run(
            [
                "docker",
                "build",
                "-f",
                "deploy/docker/Dockerfile.frontend",
                "-t",
                "ai-frontend:ci",
                ".",
            ],
            cwd=root,
            log_file=log_file,
        )
        if rc2 != 0:
            return "failed", f"log={log_file.as_posix()}"
        rc3 = _run(
            [
                "trivy",
                "image",
                "--severity",
                "CRITICAL,HIGH",
                "--exit-code",
                "1",
                "ai-backend:ci",
            ],
            cwd=root,
            log_file=log_file,
        )
        if rc3 != 0:
            return "failed", f"log={log_file.as_posix()}"
        rc4 = _run(
            [
                "trivy",
                "image",
                "--severity",
                "CRITICAL,HIGH",
                "--exit-code",
                "1",
                "ai-frontend:ci",
            ],
            cwd=root,
            log_file=log_file,
        )
        return ("passed" if rc4 == 0 else "failed", f"log={log_file.as_posix()}")

    def perf_bench():
        if ns.skip_bench or _truthy_env("CI_SKIP_BENCH"):
            return "skipped", "bench skipped"
        if ns.mode != "local":
            return "skipped", f"mode={ns.mode}"
        # Skip performance benchmark on Windows due to known ChromaDB latency issues
        import platform

        if platform.system() == "Windows":
            return "skipped", "Windows: ChromaDB latency issues (acceptable for dev)"
        uvicorn_log = logs_dir / "bench_backend_uvicorn.log"
        uvicorn_log.parent.mkdir(parents=True, exist_ok=True)
        uvicorn_fh = uvicorn_log.open("wb")
        backend_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=str(root),
            env={
                **os.environ,
                "ENVIRONMENT": "development",
                "API_ACCESS_KEY": os.environ.get("API_ACCESS_KEY", "ci-test-key"),
            },
            stdout=uvicorn_fh,
            stderr=subprocess.STDOUT,
        )
        try:
            if not _wait_for_http_200(
                "http://127.0.0.1:8000/health", timeout_seconds=30.0
            ):
                return "failed", f"log={uvicorn_log.as_posix()}"
            # Add warmup request to avoid cold start skewing results
            try:
                _http_get("http://127.0.0.1:8000/health", timeout_seconds=5.0)
                time.sleep(0.5)  # Brief pause after warmup
            except Exception:
                pass  # Warmup failure is acceptable, proceed to benchmark
            ok, details = _bench_health("http://127.0.0.1:8000/health")
            return ("passed" if ok else "failed", details)
        finally:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend_proc.kill()
            uvicorn_fh.close()

    try:
        all_ok = True
        all_ok &= _run_step(results, "Task Master validation", taskmaster_validate)
        all_ok &= _run_step(results, "System validation", system_validate)
        all_ok &= _run_step(results, "Remote smoke", remote_smoke)
        all_ok &= _run_step(results, "Backend CI parity", backend_ci)
        all_ok &= _run_step(results, "Frontend CI parity", frontend_ci)
        all_ok &= _run_step(results, "Docker Compose smoke", compose_smoke)
        all_ok &= _run_step(results, "Playwright E2E", e2e_tests)
        all_ok &= _run_step(results, "Security scans", security_scans)
        all_ok &= _run_step(results, "Trivy image scan", trivy_scan)
        all_ok &= _run_step(results, "Performance benchmark", perf_bench)
        exit_code = 0 if all_ok else 1
    finally:
        try:
            report_path = _write_validation_report(root, results, mode=ns.mode)
            print(f"Validation report: {report_path}")
        except Exception as exc:
            print(f"Validation report: failed to write ({exc})")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
