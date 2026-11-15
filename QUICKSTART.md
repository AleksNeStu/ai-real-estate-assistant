# Quick Start Guide

> 🚀 Three ways to run AI Real Estate Assistant

> Not sure which one to pick? See [DEPLOYMENT_VARIANTS.md](DEPLOYMENT_VARIANTS.md) for a feature-by-feature comparison of Local Docker, VPS, and Render free tier.

---

## 1. Local Development (Без Docker)

### Windows (PowerShell)
```powershell
.\scripts\local\run.ps1
```

### Linux/Mac (Bash)
```bash
./scripts/dev/run.sh --mode local
```

**Access:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 2. Docker Development

### Windows (PowerShell)
```powershell
# CPU mode
.\scripts\docker\cpu.ps1

# GPU mode
.\scripts\docker\gpu.ps1

# GPU + Internet access
.\scripts\docker\gpu-internet.ps1
```

### Linux/Mac (Bash)
```bash
# Auto-detect GPU
./scripts/dev/run.sh --mode docker

# Force CPU mode
./scripts/docker/docker.sh cpu

# Force GPU mode
./scripts/docker/docker.sh gpu

# Enable internet access
./scripts/dev/run.sh --mode docker --internet
```

---

## 3. Deploy to Render

See [Deployment Guide](docs/deployment/DEPLOYMENT.md) for full Render staging setup.

---

## Troubleshooting

### Frontend dependencies not installed?
```powershell
cd apps/web
npm install
cd ..
```

### Python dependencies not installed?
```powershell
cd apps/api
# The pinned manifests: runtime first, then the gate tooling, then the
# project itself - installed WITHOUT its own dependency resolution, so the
# pins in requirements.txt decide the versions.
uv pip install -r requirements.txt -r requirements-dev.txt
uv pip install --no-deps -e .
```

---

## Full Documentation

See [deployment/](deployment/) folder for detailed guides.
