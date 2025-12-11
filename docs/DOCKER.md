# 🐳 Docker Setup Guide

Run the AI Real Estate Assistant in Docker for easy deployment and consistent environments across all platforms.

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and add your API keys
nano .env  # or use any text editor

# 3. Start the application
docker-compose up -d

# 4. Open browser
# Visit: http://localhost:8501
```

### Option 2: Docker Build & Run (Python 3.12 base)

```bash
# 1. Build the image
docker build -t ai-real-estate-assistant .

# 2. Run the container
docker run -d \
  --name ai-real-estate-assistant \
  -p 8501:8501 \
  -e OPENAI_API_KEY="your-key" \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/data:/app/data \
  ai-real-estate-assistant

# 3. Open browser
# Visit: http://localhost:8501
```

---

## Configuration

### Environment Variables

Set these in your `.env` file (for docker-compose) or pass with `-e` flag (for docker run):

#### Required (at least one):
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

#### Optional:
```bash
# For local Ollama models
OLLAMA_API_BASE=http://host.docker.internal:11434

# For email notifications
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_PROVIDER=gmail
```

### Volumes

The application uses these volumes for data persistence:

- `./chroma_db` - Vector database storage
- `./data` - Property data files
- `./.preferences` - User notification preferences
- `./.notifications` - Notification history
- `./.sessions` - Session tracking data

These directories are automatically created and mounted by docker-compose.

---

## Docker Compose Commands

### Start the Application
```bash
docker-compose up -d
```

### Stop the Application
```bash
docker-compose down
```

### View Logs
```bash
# Follow logs
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```

### Restart the Application
```bash
docker-compose restart
```

### Rebuild After Code Changes
```bash
docker-compose up -d --build
```

### Remove Everything (including volumes)
```bash
docker-compose down -v
```

---

## Docker CLI Commands

### Build Image
```bash
docker build -t ai-real-estate-assistant .
```

### Run Container
```bash
docker run -d \
  --name ai-real-estate-assistant \
  -p 8501:8501 \
  -e OPENAI_API_KEY="your-openai-key" \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -v $(pwd)/data:/app/data \
  ai-real-estate-assistant
```

### View Logs
```bash
# Follow logs
docker logs -f ai-real-estate-assistant

# View last 100 lines
docker logs --tail=100 ai-real-estate-assistant
```

### Stop Container
```bash
docker stop ai-real-estate-assistant
```

### Remove Container
```bash
docker rm ai-real-estate-assistant
```

### Execute Commands Inside Container
```bash
# Open bash shell
docker exec -it ai-real-estate-assistant bash

# Run specific command
docker exec ai-real-estate-assistant ls -la
```

---

## Platform-Specific Notes

### Windows

**Docker Desktop Required**: Install from [docker.com](https://www.docker.com/products/docker-desktop)

**PowerShell Commands**:
```powershell
# Build and run
docker-compose up -d

# Use ${PWD} instead of $(pwd) for volume mounts
docker run -d `
  --name ai-real-estate-assistant `
  -p 8501:8501 `
  -e OPENAI_API_KEY="your-key" `
  -v ${PWD}/chroma_db:/app/chroma_db `
  ai-real-estate-assistant
```

**WSL2 Backend Recommended**: Enable in Docker Desktop settings for better performance.

### macOS

**Docker Desktop Required**: Install from [docker.com](https://www.docker.com/products/docker-desktop)

**Apple Silicon (M1/M2/M3)**:
- Docker automatically handles ARM64 architecture
- May need `--platform linux/amd64` for some packages:
  ```bash
  docker build --platform linux/amd64 -t ai-real-estate-assistant .
  ```

**Rosetta 2**: Enable in Docker Desktop settings for better compatibility.

### Linux

**Install Docker**:
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER
newgrp docker
```

**Install Docker Compose**:
```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

**SELinux (Fedora/RHEL)**: Add `:Z` suffix to volumes:
```bash
-v $(pwd)/chroma_db:/app/chroma_db:Z
```

---

## Using with Local Ollama

### Option 1: Ollama on Host Machine

1. Install Ollama on your host: https://ollama.ai
2. Start Ollama service
3. Set environment variable:
   ```bash
   OLLAMA_API_BASE=http://host.docker.internal:11434
   ```

### Option 2: Ollama in Docker

Uncomment the `ollama` service in `docker-compose.yml`:

```yaml
services:
  ai-real-estate-assistant:
    # ... existing config ...

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

Then:
```bash
docker-compose up -d
docker exec -it ollama ollama pull llama3.3
```

Set in your app:
```bash
OLLAMA_API_BASE=http://ollama:11434
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8501
lsof -i :8501  # Linux/macOS
netstat -ano | findstr :8501  # Windows

# Use different port
docker run -p 8502:8501 ...
# Then visit http://localhost:8502
```

### Container Keeps Restarting
```bash
# Check logs
docker logs ai-real-estate-assistant

# Common issues:
# - Missing API keys
# - Invalid environment variables
# - Port conflicts
```

### Can't Connect to Ollama
```bash
# From inside container, test connection
docker exec ai-real-estate-assistant curl http://host.docker.internal:11434

# For Linux, use host IP instead:
OLLAMA_API_BASE=http://172.17.0.1:11434
```

### Slow Performance
```bash
# Check resource limits
docker stats ai-real-estate-assistant

# Increase Docker Desktop resources:
# Settings → Resources → Increase Memory/CPU
```

### Permissions Issues (Linux)
```bash
# Fix volume permissions
sudo chown -R $USER:$USER chroma_db data .preferences .notifications .sessions
```

### Build Fails
```bash
# Clear Docker cache and rebuild
docker-compose build --no-cache

# Or for docker build:
docker build --no-cache -t ai-real-estate-assistant .
```

---

## Production Deployment

### Docker in Production

**Use docker-compose.prod.yml**:
```yaml
version: '3.8'

services:
  ai-real-estate-assistant:
    image: ai-real-estate-assistant:latest
    restart: always
    ports:
      - "80:8501"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - prod_chroma:/app/chroma_db
      - prod_data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  prod_chroma:
  prod_data:
```

**Deploy**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Behind Reverse Proxy (Nginx)

**nginx.conf**:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Health Checks

The Docker image includes a health check endpoint:
```bash
# Check from outside
curl http://localhost:8501/_stcore/health

# Check from inside
docker exec ai-real-estate-assistant curl http://localhost:8501/_stcore/health
```

---

## Development with Docker

### Live Code Reload

Mount your code directory for development:
```bash
docker run -d \
  --name ai-real-estate-assistant-dev \
  -p 8501:8501 \
  -e OPENAI_API_KEY="your-key" \
  -v $(pwd):/app \
  ai-real-estate-assistant
```

Changes to Python files will trigger Streamlit reload automatically.

### Run Tests in Docker

```bash
# Install test dependencies in container
docker exec ai-real-estate-assistant pip install pytest pytest-cov pytest-asyncio pytest-mock

# Run tests
docker exec ai-real-estate-assistant pytest tests/ -v
```

---

## Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use secrets management** - Docker secrets or external vaults for production
3. **Run as non-root user** - Add to Dockerfile for production:
   ```dockerfile
   RUN useradd -m -u 1000 appuser
   USER appuser
   ```
4. **Scan images** - Use Docker Scout or Trivy:
   ```bash
   docker scout quickview ai-real-estate-assistant
   ```
5. **Keep images updated** - Rebuild regularly with latest base image

---

## FAQ

**Q: Can I use this with Kubernetes?**
A: Yes! Convert docker-compose.yml to K8s manifests or use Kompose.

**Q: How do I backup my data?**
A: Copy the volume directories:
```bash
tar -czf backup.tar.gz chroma_db data .preferences .notifications .sessions
```

**Q: Can I run multiple instances?**
A: Yes, use different ports:
```bash
docker run -p 8502:8501 ...  # Instance 2
docker run -p 8503:8501 ...  # Instance 3
```

**Q: How do I update to latest version?**
A: Pull latest code and rebuild:
```bash
git pull
docker-compose up -d --build
```

---

For more information, see:
- [Main README](README.md) - Installation and usage
- [DEPLOYMENT.md](DEPLOYMENT.md) - Streamlit Cloud deployment
- [Docker Documentation](https://docs.docker.com/)
