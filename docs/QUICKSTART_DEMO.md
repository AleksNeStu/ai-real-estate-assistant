# 🚀 Quick Start: Local Demo

Run AI Real Estate Assistant locally with comprehensive demo data in 10 minutes.

## Prerequisites

- Windows PowerShell (or Bash on Linux/macOS)
- Docker Desktop installed and running
- Git installed

## Two Commands to Full Demo

```powershell
# Step 1: Launch Docker containers (5-8 min)
.\scripts\demo\01-launch-docker.ps1

# Step 2: Generate comprehensive demo data (2-3 min)
.\scripts\demo\02-generate-data.ps1
```

## Access Your Demo

Open your browser:

- **Frontend**: <http://localhost:3082>
- **Backend API**: <http://localhost:8082>
- **API Docs**: <http://localhost:8082/docs>

No login required — demo mode is enabled by default.

## What You Get

- 🏠 **250+ properties** across 5 Polish cities
- 👥 **50 users** with different roles
- 🔍 **100 saved searches** with diverse filters
- ⭐ **200 favorites** across users
- 🏢 **15 real estate agent profiles**
- 📊 **150 leads/inquiries**
- 📈 **300 activity events**
- ⚙️ **40 preference profiles**
- 📋 **20 CMA reports**

## Stop the Demo

```powershell
# Use the dedicated demo stop script (recommended)
.\scripts\demo\03-stop-docker.ps1

# Or use the general stop script
.\scripts\docker\stop.ps1
```

## Troubleshooting

**Containers won't start?**

```powershell
# Check Docker is running
docker ps

# Check for port conflicts
netstat -an | Select-String ":3082|:8082|:6379"
```

**Data generation fails?**

```powershell
# Re-run data generation
.\scripts\demo\02-generate-data.ps1

# Or reset everything
.\scripts\docker\reset.ps1

# Or complete data removal (careful - deletes all data!)
.\scripts\demo\04-delete-data.ps1
```

**Need more help?**
See [Demo Setup Documentation](../scripts/demo/README.md) for complete guide.

## Features to Try

1. **Property Search**: Type "2-bedroom apartment in Kraków under 500k"
2. **AI Chat**: Ask questions about properties and get instant answers
3. **Market Analytics**: View market trends and statistics
4. **Saved Searches**: Create and manage your search criteria
5. **Favorites**: Save properties you're interested in
6. **Agent Profiles**: Browse real estate professionals
7. **Lead Management**: Track property inquiries
8. **CMA Reports**: Generate comparative market analysis

## Next Steps

- Read the [Architecture Documentation](ARCHITECTURE.md)
- Explore the [API Reference](api/API_REFERENCE.md)
- Check the [Development Guide](development/CONTRIBUTING.md)
