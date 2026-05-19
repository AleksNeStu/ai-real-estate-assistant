# Demo Setup Scripts

Autonomous Process Scripts (APS) for local Docker demo environment setup.

## Quick Start (Demo Mode)

```powershell
# Step 1: Launch Docker containers
.\scripts\demo\01-launch-docker.ps1

# Step 2: Generate comprehensive demo data
.\scripts\demo\02-generate-data.ps1

# Access the demo
# Frontend: http://localhost:3082
# Backend:  http://localhost:8082
# API Docs: http://localhost:8082/docs
```

## Script Details

### 01-launch-docker.ps1

**Purpose**: Launch Docker containers with demo mode configuration

**What it does**:

- Validates Docker installation
- Creates necessary directories
- Builds and starts containers (frontend, backend, redis)
- Configures demo mode environment variables
- Performs health checks on all services
- Displays access URLs and login credentials

**Duration**: ~5-8 minutes (first run with build)

### 02-generate-data.ps1

**Purpose**: Generate comprehensive demo data for maximum feature showcase

**What it does**:

- Validates Docker containers are running
- Clears existing demo data for clean state
- Generates comprehensive mock dataset:
  - 250+ properties across 5 Polish cities
  - 50 users with different roles
  - 100 saved searches
  - 200 favorites
  - 15 real estate agent profiles
  - 150 leads/inquiries
  - 300 activity events
  - 40 preference profiles
  - 20 CMA reports
- Verifies data generation success

**Duration**: ~2-3 minutes

### 03-stop-docker.ps1

**Purpose**: Stop all Docker containers and clean up resources

**What it does**:

- Checks Docker status
- Identifies running containers
- Gracefully stops all containers (frontend, backend, redis)
- Cleans up Docker resources
- Provides restart instructions

**Duration**: ~30 seconds

### 04-delete-data.ps1

**Purpose**: Remove all demo data and containers for fresh start

**What it does**:

- Stops all containers
- Removes all Docker volumes (deletes all demo data)
- Removes orphaned containers
- Optionally removes built images to free disk space
- Requires confirmation to prevent accidental data loss

**Duration**: ~1-2 minutes (optional image removal adds time)

## Demo Data Summary

| Entity | Count | Description |
| :--- | :--- | :--- |
| **Properties** | 250+ | Apartments, houses, studios, lofts, townhouses across Kraków, Warsaw, Gdańsk, Wrocław, Poznań |
| **Users** | 50 | Various roles: user, admin, agent, premium_user |
| **Saved Searches** | 100 | Diverse search queries with different filters |
| **Favorites** | 200 | User-saved properties |
| **Agent Profiles** | 15 | Real estate professionals with agencies and licenses |
| **Leads** | 150 | Property inquiries and leads |
| **Activity Events** | 300 | User activity tracking |
| **Preference Profiles** | 40 | User preferences and requirements |
| **CMA Reports** | 20 | Comparative Market Analysis reports |

## Environment Configuration

Demo mode uses SQLite database (no PostgreSQL required):

```env
DEMO_MODE=true
NEXT_PUBLIC_DEMO_MODE=true
SEED_ON_STARTUP=true
DATABASE_URL=sqlite+aiosqlite:////app/data/demo.db
```

## Stopping the Demo

```powershell
# Use the dedicated stop script
.\scripts\demo\03-stop-docker.ps1

# Or use the general stop script
.\scripts\docker\stop.ps1

# Or use docker compose directly
cd deploy/compose
docker compose down
```

## Removing Demo Data

```powershell
# Complete data reset (removes volumes and all data)
.\scripts\demo\04-delete-data.ps1

# This will delete:
# • All database data (250+ properties, users, etc.)
# • All Docker volumes
# • All containers
# • Optionally: built images (for complete cleanup)
```

## Troubleshooting

### Backend container not running

```powershell
# Check container status
docker ps -a | Select-String ai-backend

# View backend logs
docker logs ai-backend
```

### Port conflicts

```powershell
# Check if ports are in use
netstat -an | Select-String ":3082|:8082|:6379"

# Stop conflicting services or modify ports in deploy/compose/docker-compose.yml
```

### Database errors

```powershell
# Re-run data generation script
.\scripts\demo\02-generate-data.ps1

# Or reset everything
.\scripts\docker\reset.ps1
```

## Demo Features Available

With comprehensive demo data, all features are fully functional:

- ✅ Property search with 250+ listings
- ✅ AI chat with mock responses
- ✅ Market analytics and trends
- ✅ Saved searches and favorites
- ✅ Agent profiles and management
- ✅ Lead tracking and management
- ✅ User activity monitoring
- ✅ Preference profiles
- ✅ CMA reports
- ✅ Notifications system

## Next Steps After Demo Setup

1. Open <http://localhost:3082> in your browser
2. Explore property search with diverse listings
3. Test AI chat with comprehensive data
4. Try saved searches, favorites, and analytics
5. Experience ALL features with maximum demo data
