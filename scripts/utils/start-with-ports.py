#!/usr/bin/env python3
"""
Enhanced startup script with automatic port allocation.

This script provides dynamic port allocation for
AI Real Estate Assistant, preventing port conflicts when running
multiple similar projects simultaneously.

Usage:
    python scripts/start-with-ports.py                    # Start both
    python scripts/start-with-ports.py --service backend  # Backend only
    python scripts/start-with-ports.py --service frontend # Frontend only
    python scripts/start-with-ports.py --dry-run          # Show commands
    python scripts/start-with-ports.py --allocate-ports   # Allocate ports

Features:
    - Auto-detect available ports in configured ranges
    - Cross-platform support (windows, macOS, linux)
    - Service discovery between frontend and backend
    - Integration with parent port registry
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add the scripts directories to path for imports:
# `service_discovery` lives next to this file, `port.port_manager` one level up.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from service_discovery import ServiceDiscovery


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    """Build the uvicorn command, preferring the provisioned virtualenv."""
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


def _build_backend_env(*, port: int, root: Path) -> dict[str, str]:
    """Build environment variables for backend service."""
    env = os.environ.copy()
    env.setdefault("ENVIRONMENT", "development")
    if (
        not env.get("API_ACCESS_KEY", "").strip()
        and not env.get("API_ACCESS_KEYS", "").strip()
    ):
        env["API_ACCESS_KEY"] = "dev-secret-key"
    env["PORT"] = str(port)
    # Add apps/api to PYTHONPATH for correct imports
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
    frontend_port: int = 3800,
    root: Path | None = None,
) -> dict[str, str]:
    """Build environment variables for frontend service."""
    env = os.environ.copy()
    env.setdefault("NEXT_PUBLIC_API_URL", "/api/v1")
    env.setdefault("BACKEND_API_URL", f"http://localhost:{backend_port}/api/v1")
    env.setdefault("BACKEND_PORT", str(backend_port))
    # The launcher owns the bind port: an ambient PORT must not win.
    env["PORT"] = str(frontend_port)
    env["FRONTEND_PORT"] = str(frontend_port)
    if (
        not env.get("API_ACCESS_KEY", "").strip()
        and not env.get("API_ACCESS_KEYS", "").strip()
    ):
        effective_backend_key = backend_env.get("API_ACCESS_KEY", "").strip()
        if effective_backend_key:
            env["API_ACCESS_KEY"] = effective_backend_key
    # Add node_modules/.bin to PATH for Windows
    if root is not None and os.name == "nt":
        bin_path = str(root / "apps" / "web" / "node_modules" / ".bin")
        if os.path.isdir(bin_path):
            existing_path = env.get("PATH", "")
            env["PATH"] = f"{bin_path}{os.pathsep}{existing_path}"
    return env


def _print_dry_run(
    wants_backend: bool,
    wants_frontend: bool,
    backend_cmd: list[str],
    frontend_cmd: list[str],
    env_backend: dict[str, str],
    env_frontend: dict[str, str],
    backend_port: int,
    frontend_port: int,
    root: Path,
) -> None:
    """Print dry run information."""
    print("\n=== DRY RUN - Commands that would be executed ===\n")
    if wants_backend:
        print(f"Backend (port {backend_port}):")
        print(f"  {' '.join(backend_cmd)}")
        py_path = env_backend.get("PYTHONPATH", "")
        print(f"  PYTHONPATH={py_path}")
    if wants_frontend:
        print(f"\nFrontend (port {frontend_port}):")
        print(f"  cd apps/web && {' '.join(frontend_cmd)}")
        be_url = env_frontend.get("BACKEND_API_URL", "")
        print(f"  BACKEND_API_URL={be_url}")
    print(f"\nPort registry: {root / 'docs' / 'PORT_REGISTRY.json'}")
    print(f"Service discovery: {root / '.env.ports'}")


def _start_services(
    wants_backend: bool,
    wants_frontend: bool,
    backend_cmd: list[str],
    frontend_cmd: list[str],
    env_backend: dict[str, str],
    env_frontend: dict[str, str],
    backend_port: int,
    frontend_port: int,
    root: Path,
) -> int:
    """Start services and wait for them to complete."""
    procs: list[subprocess.Popen[bytes]] = []
    try:
        if wants_backend:
            print(f"Starting backend on port {backend_port}...")
            procs.append(subprocess.Popen(backend_cmd, cwd=str(root), env=env_backend))

        if wants_frontend:
            print(f"Starting frontend on port {frontend_port}...")
            procs.append(
                subprocess.Popen(
                    frontend_cmd, cwd=str(root / "apps" / "web"), env=env_frontend
                )
            )

        print("\nServices running:")
        if wants_backend:
            print(f"  Backend:  http://localhost:{backend_port}")
            print(f"  API Docs: http://localhost:{backend_port}/docs")
        if wants_frontend:
            print(f"  Frontend: http://localhost:{frontend_port}")
        print("\nPress Ctrl+C to stop all services")

        # Wait for processes
        while True:
            for proc in procs:
                code = proc.poll()
                if code is not None:
                    for other in procs:
                        if other is not proc and other.poll() is None:
                            other.terminate()
                    return int(code)
            import time

            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping services...")
        for proc in procs:
            if proc.poll() is None:
                proc.terminate()
        return 130


def main(argv: list[str] | None = None) -> int:
    """Main entry point for start-with-ports script."""
    parser = argparse.ArgumentParser(
        description="Start services with dynamic port allocation"
    )
    parser.add_argument(
        "--service",
        choices=["all", "backend", "frontend"],
        default="all",
        help="Which service(s) to start",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show commands without executing"
    )
    parser.add_argument(
        "--no-bootstrap", action="store_true", help="Skip dependency installation"
    )
    parser.add_argument(
        "--backend-port", type=int, default=None, help="Preferred backend port"
    )
    parser.add_argument(
        "--frontend-port", type=int, default=None, help="Preferred frontend port"
    )
    parser.add_argument(
        "--allocate-ports", action="store_true", help="Force port allocation"
    )
    parser.add_argument(
        "--release-on-exit",
        action="store_true",
        help="Release port allocations when services stop",
    )
    args = parser.parse_args(argv)

    root = _project_root()

    # Initialize service discovery
    sd = ServiceDiscovery(root)

    # Allocate or get ports
    if args.allocate_ports or not sd.port_manager.get_allocation(
        sd.BACKEND_SERVICE_NAME
    ):
        print("Allocating ports...")
        backend_port, frontend_port = sd.ensure_ports_configured(
            preferred_backend=args.backend_port, preferred_frontend=args.frontend_port
        )
    else:
        ports = sd.get_ports()
        backend_port = ports.get("backend", args.backend_port or 8000)
        frontend_port = ports.get("frontend", args.frontend_port or 3800)
        print(f"Using existing ports: backend={backend_port}, frontend={frontend_port}")

    # Build commands
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

    wants_backend = args.service in {"all", "backend"}
    wants_frontend = args.service in {"all", "frontend"}

    if args.dry_run:
        _print_dry_run(
            wants_backend,
            wants_frontend,
            backend_cmd,
            frontend_cmd,
            env_backend,
            env_frontend,
            backend_port,
            frontend_port,
            root,
        )
        return 0

    try:
        return _start_services(
            wants_backend,
            wants_frontend,
            backend_cmd,
            frontend_cmd,
            env_backend,
            env_frontend,
            backend_port,
            frontend_port,
            root,
        )
    finally:
        if args.release_on_exit:
            print("Releasing port allocations...")
            sd.release_all()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
