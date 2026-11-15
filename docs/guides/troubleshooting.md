# Troubleshooting Guide

This guide covers common issues and solutions when developing or deploying the AI Real Estate Assistant.

## Table of Contents

- [Development Issues](#development-issues)
- [Docker Issues](#docker-issues)
- [Backend Issues](#backend-issues)
- [Frontend Issues](#frontend-issues)
- [Database Issues](#database-issues)
- [CI/CD Issues](#cicd-issues)
- [Deployment Issues](#deployment-issues)
- [Performance Issues](#performance-issues)

---

## Development Issues

### Port Already in Use

**Symptom:** `Error: listen EADDRINUSE: address already in use :::8000`

**Solution:**

```powershell
# Windows: Find process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Windows: Find process on port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

### NumPy Import Error (Windows)

**Symptom:**
```
ImportError: Unable to import required dependencies:
numpy: Error importing numpy from its source directory
```

**Solution:**
```powershell
deactivate
Remove-Item -Recurse -Force .\.venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pip install --no-deps -e .
python -c "import numpy; print('NumPy OK')"
```

### Pandas C Extension Error

**Symptom:**
```
ModuleNotFoundError: No module named 'pandas._libs.pandas_parser'
```

**Solution:**
```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-cache-dir --force-reinstall "pandas>=2.2.0,<2.3.0"
```

### Pydantic-Core Error

**Symptom:**
```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```

**Solution:**
```powershell
python -m pip install "numpy>=1.24.0,<2.0.0"
python -m pip install --no-cache-dir "pydantic-core>=2.14.0,<3.0.0"
python -m pip install --no-cache-dir "pandas>=2.2.0,<2.3.0"
python -m pip install -r requirements.txt
```

---

## Docker Issues

### Container Exits Immediately

**Symptom:** Docker container starts and exits immediately.

**Solution:**
```bash
# Check logs
docker compose logs backend

# Common issue: Missing API keys
# Edit .env and add required keys

# Verify .env is loaded correctly
docker compose config
```

### GPU Not Detected

**Symptom:** Ollama GPU container doesn't use GPU.

**Solution:**
```bash
# Verify NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Install NVIDIA Container Toolkit
# See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

# Check GPU is available
docker compose ps
```

### Volume Permission Issues

**Symptom:** Permission denied when writing to mounted volumes.

**Solution:**
```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./chroma_db ./data

# Or run with user flag
docker compose -f deploy/compose/docker-compose.yml --user $(id -u):$(id -g) up
```

### Out of Disk Space

**Symptom:** Docker build fails with "no space left on device".

**Solution:**
```bash
# Clean unused images
docker image prune -a

# Clean unused volumes
docker volume prune

# Clean everything
docker system prune -a --volumes
```

---

## Backend Issues

### API Key Not Recognized

**Symptom:** `401 Unauthorized` responses.

**Solution:**
1. Ensure `.env` exists in project root
2. Check variable name: `API_ACCESS_KEY`
3. Restart services after editing `.env`
4. Verify no extra spaces in `.env`

### CORS Errors in Browser

**Symptom:** Browser console shows CORS policy errors.

**Solution:**
- Development: Set `ENVIRONMENT=development` (allows all origins)
- Production: Set `CORS_ALLOW_ORIGINS` to your frontend URL
```bash
# In .env
ENVIRONMENT=production
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### ChromaDB Persistence Issues

**Symptom:** Data not persisting between restarts.

**Solution:**
```bash
# Reset ChromaDB
Remove-Item -Recurse -Force .\chroma_db

# Restart app - database will be recreated
```

### ChromaDB Metadata Errors

**Symptom:**
```
Error adding batch: Expected metadata value of type 'string', 'number', 'boolean' or 'null'
```

**Cause:** Non-primitive values in document metadata.

**Solution:**
- Ensure only primitives (str/int/float/bool/None) in metadata
- Convert datetimes to ISO 8601 strings
- Avoid nesting dicts/lists

### LLM Provider Not Available

**Symptom:** "runtime_available=false" for LLM provider.

**Solution:**
1. Verify API key is correct
2. Check provider service status
3. Verify network connectivity
4. Check provider billing/quota

---

## Frontend Issues

### Build Fails

**Symptom:** Build fails locally or in CI.

**Solution:**
```bash
# Clear cache and reinstall
cd apps/web
rm -rf node_modules .next
npm install
npm run build
```

### Module Not Found

**Symptom:** `Module not found: Can't resolve '@/<module>'`

**Solution:**
1. Check `tsconfig.json` paths configuration
2. Verify file exists at expected location
3. Restart TypeScript server in IDE

### Hydration Errors

**Symptom:** "Hydration failed" or "Text content does not match".

**Solution:**
1. Avoid using `Date()` or `Math.random()` directly in components
2. Use `useEffect` for client-only values
3. Ensure server and client render same markup

### State Not Persisting

**Symptom:** Settings reset on page refresh.

**Solution:**
1. Check state is saved to localStorage/sessionStorage
2. Verify state restoration logic on mount
3. Check for localStorage quota exceeded

---

## Database Issues

### Connection Pool Exhausted

**Symptom:** "Pool exhausted" or "Connection timeout".

**Solution:**
```bash
# In .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT_SECONDS=60
```

### Migration Conflicts

**Symptom:** Migration fails due to conflicts.

**Solution:**
```bash
# Rollback to last working version
alembic downgrade base

# Resolve conflicts
# Then create new migration
alembic revision --autogenerate -m "fix conflict"
alembic upgrade head
```

### SQLite Lock Errors

**Symptom:** "database is locked" errors.

**Solution:**
```bash
# Ensure only one process is accessing the database
# Use WAL mode for better concurrency
# In code:
# engine = create_engine("sqlite:///file.db?check_same_thread=False", connect_args={"timeout": 30})
```

---

## CI/CD Issues

### Integration Test Flake

**Symptom:** Tests pass locally, fail in CI intermittently.

**Cause:** Async indexing racing with shared in-memory Chroma state.

**Solution:**
- CI retries integration tests once automatically
- Add explicit waits in tests
- Consider using file-backed Chroma for tests

### Coverage Gate Failure

**Symptom:** New code doesn't meet coverage requirements.

**Solution:**
```bash
# Check coverage locally
pytest tests/unit --cov=. --cov-report=html
open htmlcov/index.html

# Find uncovered lines and write tests
```

### Semgrep Not Available

**Symptom:** `semgrep: command not found`.

**Solution:**
```bash
# Install Semgrep
python -m pip install semgrep

# Or use Docker
docker pull returntocorp/semgrep
```

### npm EPERM on Windows

**Symptom:** `npm ci` fails with EPERM.

**Solution:**
```powershell
# Delete node_modules and reinstall
Remove-Item -Recurse -Force apps/web/node_modules
cd apps/web
npm ci
```

---

## Deployment Issues

### 502 Bad Gateway

**Symptom:** Reverse proxy returns 502.

**Solution:**
```bash
# Check backend is running
docker compose ps
# or
sudo systemctl status ai-backend

# Check logs
docker compose logs backend
# or
sudo journalctl -u ai-backend -n 50

# Verify port configuration
# Nginx/Apache proxy_pass should match backend port
```

### SSL Certificate Errors

**Symptom:** Browser shows certificate warnings.

**Solution:**
```bash
# Renew certificate
sudo certbot renew

# Force renewal
sudo certbot renew --force-renewal

# Check certificate
sudo certbot certificates
```

### High Memory Usage

**Symptom:** Server runs out of memory.

**Solution:**
1. Add swap space
2. Configure Redis max memory
3. Set `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`
4. Consider adding more RAM

---

## Performance Issues

### Slow Response Times

**Symptom:** API responses take >10 seconds.

**Solution:**
1. Enable Redis caching
2. Check LLM provider latency
3. Consider using faster model (e.g., gpt-4o-mini)
4. Add response caching
5. Optimize database queries

### Memory Leaks

**Symptom:** Memory usage increases over time.

**Solution:**
```bash
# Monitor memory usage
docker stats

# Restart containers periodically
# Or investigate memory leaks in Python code
```

### Database Slow Queries

**Symptom:** Queries take too long.

**Solution:**
1. Add database indexes
2. Use connection pooling
3. Enable query logging to identify slow queries
4. Consider adding Redis caching for frequent queries

---

## Getting Help

### Debug Mode

Enable verbose logging:

```bash
# In .env
ENVIRONMENT=development
LOG_LEVEL=debug
```

### Collect Debug Information

```bash
# System info
uname -a
docker --version
docker compose version

# Python info
python --version
pip list

# Node info
node --version
npm --version

# Logs
docker compose logs > deployment-logs.txt
```

### Where to Ask

1. Check existing [GitHub Issues](https://github.com/AleksNeStu/ai-real-estate-assistant/issues)
2. Create new issue with:
   - Error message
   - Steps to reproduce
   - Environment details
   - Logs

---

## Related Documentation

- [Local Development Guide](local-development.md)
- [Environment Setup Guide](environment-setup.md)
- [Deployment Guide](deployment.md)
- [Testing Guide](testing.md)
