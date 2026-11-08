#!/usr/bin/env python3
"""
Mode-aware launcher for AI Real Estate Assistant.

The PowerShell and shell wrappers under scripts/ are thin argument forwarders;
this module is the single place that decides HOW the stack comes up.

Usage:
    python scripts/start.py                              # auto (docker if present, else local)
    python scripts/start.py --mode local                 # local processes, no Docker
    python scripts/start.py --mode docker                # Docker Compose stack
    python scripts/start.py --mode docker --docker-mode gpu --internet
    python scripts/start.py --mode local --service backend --dry-run

Modes:
    --mode auto | docker | local
    --service all | backend | frontend
    --docker-mode auto | cpu | gpu | ask
    --internet          enable the internet profile (web search)
    --dry-run           print the commands instead of running them
    --no-bootstrap      skip dependency installation
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_checked(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True, env=env)


def _has_docker_compose() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _get_default_api_access_key_from_env() -> str:
    raw = os.environ.get("API_ACCESS_KEY", "").strip()
    if raw:
        return raw
    rotated = os.environ.get("API_ACCESS_KEYS", "")
    if not rotated:
        return ""
    first = next((v.strip() for v in rotated.split(",") if v.strip()), "")
    return first


def _ensure_uv_dev_env(root: Path) -> None:
    _run_checked(
        [sys.executable, str(root / "scripts" / "setup" / "bootstrap.py"), "--dev"],
        cwd=root,
    )


def _ensure_npm_env(root: Path) -> None:
    web_dir = root / "apps" / "web"
    if not (web_dir / "node_modules").exists():
        print("Frontend dependencies not found. Installing...")
        npm = "npm.cmd" if os.name == "nt" else "npm"
        _run_checked([npm, "install"], cwd=web_dir)


def _docker_gpu_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "run", "--rm", "--gpus", "all", "alpine:3.20", "true"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False


def _choose_docker_mode_interactively(*, default_mode: str) -> str:
    if not sys.stdin or not sys.stdin.isatty():
        return default_mode
    print("Select Docker mode:")
    print("  1) auto (GPU if available, else CPU)")
    print("  2) cpu")
    print("  3) gpu")
    raw = input(f"Choice [default: {default_mode}]: ").strip()
    if not raw:
        return default_mode
    if raw == "1":
        return "auto"
    if raw == "2":
        return "cpu"
    if raw == "3":
        return "gpu"
    if raw.lower() in {"auto", "cpu", "gpu"}:
        return raw.lower()
    return default_mode


def _run_docker(root: Path, *, profiles: list[str]) -> int:
    if not _has_docker_compose():
        print(
            "Docker Compose is not available. Run with --mode local.", file=sys.stderr
        )
        return 2
    env = os.environ.copy()
    if "local-llm" in profiles:
        ollama_api_base = "http://ollama:11434"
        if "gpu" in profiles:
            ollama_api_base = "http://ollama_gpu:11434"
        env.setdefault("OLLAMA_API_BASE", ollama_api_base)
        env.setdefault("OLLAMA_HOST", ollama_api_base)
    if "internet" in profiles:
        env.setdefault("INTERNET_ENABLED", "true")
    cmd = ["docker", "compose", "-f", "deploy/compose/docker-compose.yml"]
    for profile in profiles:
        cmd.extend(["--profile", profile])
    cmd.extend(["up", "--build"])
    subprocess.run(cmd, cwd=str(root), env=env)
    return 0


def _sanitize_env_for_display(env: dict[str, str]) -> dict[str, str]:
    redacted_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    safe: dict[str, str] = {}
    for k, v in env.items():
        if any(marker in k.upper() for marker in redacted_markers):
            safe[k] = "<redacted>"
        else:
            safe[k] = v
    return safe


def _venv_python(root: Path) -> Path | None:
    """Return the backend virtualenv interpreter, if it is provisioned."""
    candidates = (
        root / "apps" / "api" / ".venv" / "Scripts" / "python.exe",
        root / "apps" / "api" / ".venv" / "bin" / "python",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _backend_cmd(root: Path, port: int) -> list[str]:
    """Build the uvicorn command for the local mode.

    Preference order:
      1. the project virtualenv (already provisioned, fastest start),
      2. `uv run` against apps/api (syncs apps/api/uv.lock),
      3. the interpreter that runs this launcher.
    """
    uvicorn_args = [
        "uvicorn",
        "api.main:app",
        "--reload",
        "--reload-dir",
        str(root / "apps" / "api"),
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    venv_python = _venv_python(root)
    if venv_python is not None:
        return [str(venv_python), "-m", *uvicorn_args]
    if shutil.which("uv") is not None:
        return ["uv", "run", "--project", str(root / "apps" / "api"), *uvicorn_args]
    return [sys.executable, "-m", *uvicorn_args]


def _build_backend_env(
    *, port: int | None = None, root: Path | None = None
) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("ENVIRONMENT", "development")
    if (
        not env.get("API_ACCESS_KEY", "").strip()
        and not env.get("API_ACCESS_KEYS", "").strip()
    ):
        env["API_ACCESS_KEY"] = "dev-secret-key"
    if port is not None:
        env["PORT"] = str(port)
    # Add apps/api to PYTHONPATH for correct imports
    if root is not None:
        api_path = str(root / "apps" / "api")
        existing_pythonpath = env.get("PYTHONPATH", "")
        if existing_pythonpath:
            env["PYTHONPATH"] = f"{api_path}{os.pathsep}{existing_pythonpath}"
        else:
            env["PYTHONPATH"] = api_path
    return env


def _build_frontend_env(
    *,
    backend_env: dict[str, str],
    backend_port: int = 8000,
    frontend_port: int = 3000,
    root: Path | None = None,
) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("NEXT_PUBLIC_API_URL", "/api/v1")
    env.setdefault("BACKEND_API_URL", f"http://localhost:{backend_port}/api/v1")
    # The launcher owns the bind port: an ambient PORT must not win.
    env["PORT"] = str(frontend_port)
    if (
        not env.get("API_ACCESS_KEY", "").strip()
        and not env.get("API_ACCESS_KEYS", "").strip()
    ):
        effective_backend_key = (
            backend_env.get("API_ACCESS_KEY", "").strip()
            or _get_default_api_access_key_from_env()
        )
        if effective_backend_key:
            env["API_ACCESS_KEY"] = effective_backend_key
    # Add node_modules/.bin to PATH for Windows (so npm can find next, etc.)
    if root is not None and os.name == "nt":
        bin_path = str(root / "apps" / "web" / "node_modules" / ".bin")
        if os.path.isdir(bin_path):
            existing_path = env.get("PATH", "")
            env["PATH"] = f"{bin_path}{os.pathsep}{existing_path}"
    return env


def _run_local(
    root: Path,
    *,
    service: str,
    no_bootstrap: bool,
    dry_run: bool,
    backend_port: int = 8000,
    frontend_port: int = 3000,
) -> int:
    wants_backend = service in {"all", "backend"}
    wants_frontend = service in {"all", "frontend"}

    backend_cmd = _backend_cmd(root, backend_port)
    frontend_cmd = ["npm", "run", "dev"]
    if os.name == "nt":
        frontend_cmd[0] = "npm.cmd"

    env_backend = _build_backend_env(port=backend_port, root=root)
    env_frontend = _build_frontend_env(
        backend_env=env_backend,
        backend_port=backend_port,
        frontend_port=frontend_port,
        root=root,
    )

    if dry_run:
        if wants_backend:
            print("BACKEND_CMD:", " ".join(backend_cmd))
        if wants_frontend:
            print("FRONTEND_CMD:", " ".join(frontend_cmd))
        if wants_backend:
            print(
                "BACKEND_ENV:",
                _sanitize_env_for_display(
                    {
                        k: env_backend[k]
                        for k in sorted(env_backend)
                        if k
                        in {
                            "ENVIRONMENT",
                            "API_ACCESS_KEY",
                            "API_ACCESS_KEYS",
                            "PYTHONPATH",
                        }
                    }
                ),
            )
        if wants_frontend:
            keys = {
                "NEXT_PUBLIC_API_URL",
                "BACKEND_API_URL",
                "API_ACCESS_KEY",
                "API_ACCESS_KEYS",
                "PORT",
            }
            print(
                "FRONTEND_ENV:",
                _sanitize_env_for_display(
                    {k: env_frontend[k] for k in sorted(env_frontend) if k in keys}
                ),
            )
        return 0

    if wants_frontend and shutil.which("npm") is None:
        print("npm is not installed or not on PATH.", file=sys.stderr)
        return 2

    if wants_frontend and not no_bootstrap:
        _ensure_npm_env(root)

    if wants_backend and not no_bootstrap and _venv_python(root) is None:
        # No provisioned virtualenv: bootstrap one with uv.
        if shutil.which("uv") is None:
            print("uv is not installed or not on PATH.", file=sys.stderr)
            print("Install it with: pip install uv", file=sys.stderr)
            return 2
        _ensure_uv_dev_env(root)

    procs: list[subprocess.Popen[bytes]] = []
    try:
        if wants_backend:
            procs.append(subprocess.Popen(backend_cmd, cwd=str(root), env=env_backend))
        if wants_frontend:
            procs.append(
                subprocess.Popen(
                    frontend_cmd, cwd=str(root / "apps" / "web"), env=env_frontend
                )
            )

        while True:
            for proc in procs:
                code = proc.poll()
                if code is not None:
                    for other in procs:
                        if other is not proc and other.poll() is None:
                            other.terminate()
                    return int(code)
    except KeyboardInterrupt:
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        return 130


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "docker", "local"], default="auto")
    parser.add_argument(
        "--service", choices=["all", "backend", "frontend"], default="all"
    )
    parser.add_argument(
        "--docker-mode", choices=["auto", "cpu", "gpu", "ask"], default="auto"
    )
    parser.add_argument("--docker-profile", action="append", default=[])
    parser.add_argument("--internet", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-bootstrap", action="store_true")
    parser.add_argument(
        "--backend-port", type=int, default=8000, help="Backend port (default: 8000)"
    )
    parser.add_argument(
        "--frontend-port", type=int, default=3000, help="Frontend port (default: 3000)"
    )
    args = parser.parse_args(argv)
    if bool(args.internet):
        os.environ.setdefault("INTERNET_ENABLED", "true")

    root = _project_root()
    docker_mode = str(args.docker_mode)
    if docker_mode == "ask":
        docker_mode = _choose_docker_mode_interactively(default_mode="auto")

    requested_profiles = [p for p in args.docker_profile if p and p.strip()]
    effective_profiles = list(requested_profiles)
    if bool(args.internet) and "internet" not in effective_profiles:
        effective_profiles.append("internet")
    if docker_mode == "gpu":
        if "gpu" not in effective_profiles:
            effective_profiles.append("gpu")
        if "local-llm" not in effective_profiles:
            effective_profiles.append("local-llm")
    elif docker_mode == "auto":
        if "gpu" not in effective_profiles and _docker_gpu_available():
            effective_profiles.append("gpu")

    if args.mode == "auto":
        if _has_docker_compose():
            if args.dry_run:
                prefix = "docker compose -f deploy/compose/docker-compose.yml"
                profiles = " ".join(f"--profile {p}" for p in effective_profiles)
                cmd = f"{prefix} {profiles} up --build".strip()
                cmd = " ".join(cmd.split())
                print(f"DOCKER_CMD: {cmd}")
                return 0
            return _run_docker(root, profiles=effective_profiles)
        return _run_local(
            root,
            service=args.service,
            no_bootstrap=bool(args.no_bootstrap),
            dry_run=bool(args.dry_run),
            backend_port=args.backend_port,
            frontend_port=args.frontend_port,
        )
    if args.mode == "docker":
        if args.dry_run:
            prefix = "docker compose -f deploy/compose/docker-compose.yml"
            profiles = " ".join(f"--profile {p}" for p in effective_profiles)
            cmd = f"{prefix} {profiles} up --build".strip()
            cmd = " ".join(cmd.split())
            print(f"DOCKER_CMD: {cmd}")
            return 0
        return _run_docker(root, profiles=effective_profiles)
    return _run_local(
        root,
        service=args.service,
        no_bootstrap=bool(args.no_bootstrap),
        dry_run=bool(args.dry_run),
        backend_port=args.backend_port,
        frontend_port=args.frontend_port,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
