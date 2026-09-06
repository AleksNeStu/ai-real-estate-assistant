# 💻 Local Demo — Quick Reference

## Run Demo Locally (10 min)

```powershell
# Step 1: Launch Docker (5-8 min)
.\scripts\demo\01-launch-docker.ps1

# Step 2: Generate Data (2-3 min)
.\scripts\demo\02-generate-data.ps1

# Open browser
# Frontend: http://localhost:3082
# Backend:  http://localhost:8082
# API Docs: http://localhost:8082/docs
```

## Stop Demo

```powershell
# Use dedicated demo stop script
.\scripts\demo\03-stop-docker.ps1

# Or use general stop script
.\scripts\docker\stop.ps1
```

## Delete All Demo Data

```powershell
# Complete data removal (careful - deletes everything!)
.\scripts\demo\04-delete-data.ps1
```

## What's Included

- 250+ properties across 5 Polish cities
- 50 users with different roles
- 100 saved searches, 200 favorites
- 15 agents, 150 leads, 300 activity events
- 40 preference profiles, 20 CMA reports

## Need Help?

See [docs/development/QUICKSTART_DEMO.md](docs/development/QUICKSTART_DEMO.md) or [scripts/demo/README.md](scripts/demo/README.md)

For a feature-by-feature comparison of Local Docker vs VPS vs Render free tier, see [DEPLOYMENT_VARIANTS.md](DEPLOYMENT_VARIANTS.md).
