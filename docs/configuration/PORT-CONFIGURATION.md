# Port Configuration

This document explains the port allocation strategy for the AI Real Estate Assistant monorepo.

## Port Ranges

| Service | Local Port | Docker Port | Purpose |
|---------|------------|-------------|---------|
| Backend API | 8001 | 8082 → 8000 | FastAPI backend |
| Frontend Web | 3800 | 3082 → 3000 | Next.js frontend |
| PostgreSQL | 5432 | 5432 | Database |
| Redis | 6379 | 16379 | Cache/sessions |
| Adminer | 8081 | 8081 | DB admin UI |
| SearXNG | 8080 | 8081 | Web search (optional) |
| Ollama | 11434 | 11434 | Local LLM (optional) |

## Local Development Ports

Local development uses **auto-discovery** to find available ports:

```bash
# Auto-discover and allocate ports
python scripts/service_discovery.py

# Output: .env.ports file with allocated ports
```

The `.env.ports` file is auto-generated and contains:

```bash
BACKEND_PORT=8001
BACKEND_URL=http://localhost:8001
BACKEND_API_URL=http://localhost:8001/api/v1

FRONTEND_PORT=3800
FRONTEND_URL=http://localhost:3800

CORS_ALLOW_ORIGINS=http://localhost:3800

NEXT_PUBLIC_API_URL=/api/v1
```

### Port Range Conventions

| Category | Range | Notes |
|----------|-------|-------|
| Frontend | 3800-3899 | Next.js development servers |
| Backend | 8000-8099 | FastAPI backend services |
| AI/MCP | 9000-9099 | AI model serving, MCP connectors |
| Infrastructure | 5432, 6379, etc. | Standard service ports |

## Docker Ports

Docker Compose uses different port mappings:

```yaml
# deploy/compose/docker-compose.yml
services:
  backend:
    ports:
      - "8082:8000"  # External:Internal

  frontend:
    ports:
      - "3082:3000"  # External:Internal
```

### Why Different Ports?

- **Local**: Ports 8001/3800 avoid conflicts with common defaults
- **Docker**: Ports 8082/3082 allow Docker and local dev to run simultaneously
- **Production**: Internal container ports (8000/3000) are standard

## Environment Variables

### Backend (apps/api/)

```bash
# Port is derived from DATABASE_URL or hardcoded
# Backend runs on port from PORT env var or 8001
PORT=8001
```

### Frontend (apps/web/)

```bash
# Server-side API proxy target
BACKEND_API_URL=http://localhost:8001/api/v1

# Client-side API path (uses Next.js proxy)
NEXT_PUBLIC_API_URL=/api/v1
```

## CORS Configuration

CORS must match the frontend origin:

| Environment | CORS_ALLOW_ORIGINS |
|-------------|-------------------|
| Local | `http://localhost:3800` |
| Docker | `http://localhost:3082` |
| Production | `https://your-domain.com` |

**Important**: Production requires explicit origins (no wildcards).

## Port Conflicts

If you get a "port already in use" error:

### Windows

```powershell
# Find process using port
netstat -ano | findstr :8001

# Kill process (replace PID)
taskkill /PID <PID> /F
```

### Linux/macOS

```bash
# Find process using port
lsof -i :8001

# Kill process (replace PID)
kill -9 <PID>
```

## Best Practices

1. **Never commit `.env.ports`** - It's auto-generated
2. **Use service discovery** - Run `python scripts/service_discovery.py` on first setup
3. **Check port availability** - Before starting services
4. **Update CORS** - When changing ports

## Related Files

- [`.env.ports`](/.env.ports) - Auto-generated port configuration
- [`scripts/service_discovery.py`](/scripts/service_discovery.py) - Port discovery script
- [`deploy/compose/docker-compose.yml`](/deploy/compose/docker-compose.yml) - Docker port mappings
