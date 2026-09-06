# Development Scripts Guide

This project provides a set of scripts in `scripts/` to streamline development tasks. These scripts call the shared Python launcher (`scripts/start.py`) to ensure consistent execution across environments.

## Recommended Entry Point

Pick one script from `scripts/local/` or `scripts/docker/`.

Advanced usage (all flags supported):

```powershell
python .\scripts\start.py --help
```

## Script Layout

Use these subfolders to avoid a flat list of scripts:

- `scripts/local/` (local runs)
- `scripts/docker/` (docker runs)

## Local Development (Recommended)
Run the application directly on your host machine. Requires Python (uv) and Node.js installed.

| Script | Description |
|--------|-------------|
| `local/run.ps1` | Starts both Backend and Frontend. |
| `local/run-internet.ps1` | Starts Backend/Frontend with **Web Search enabled**. |
| `local/backend.ps1` | Starts only the Backend API (port 8000). |
| `local/frontend.ps1` | Starts only the Frontend Next.js app (port 3000). |

## Docker Development
Run the application in isolated containers. Useful for consistent environments or testing deployment.

| Script | Description |
|--------|-------------|
| `docker/cpu.ps1` | Runs in Docker without GPU. |
| `docker/gpu.ps1` | Runs in Docker with NVIDIA GPU passed through (requires NVIDIA Container Toolkit). |
| `docker/gpu-internet.ps1` | Docker + GPU + **SearxNG** container for private web search. |
| `docker/cpu-internet.ps1` | Docker + CPU + **SearxNG** container. |

## CI & Maintenance

| Script | Description |
|--------|-------------|
| `ci/run-full.ps1` | Runs the full suite of CI checks (lint, test, security, build). Run this before pushing! |
| `env/setup.ps1` | Bootstraps the development environment (installs dependencies). |

## Key Differences

### 1. Local vs Docker
- **Local**: Faster iteration (hot reload works better), uses your system's resources directly.
- **Docker**: Isolated, exact replica of production, but file syncing/hot reload can be slower on Windows.

### 2. CPU vs GPU
- **Local**: Automatically uses your GPU if `torch` with CUDA is installed in your venv.
- **Docker**: Use `scripts/docker/gpu.ps1` (requires NVIDIA Container Toolkit).

### 3. Internet Mode
- **Local**: Uses `DuckDuckGo` (via HTML scraping) by default. Zero setup required.
- **Docker**: Starts a dedicated `SearxNG` container for privacy-preserving search.
