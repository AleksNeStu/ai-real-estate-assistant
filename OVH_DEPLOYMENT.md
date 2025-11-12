# OVH Cloud Deployment Guide

Complete guide for deploying AI Real Estate Assistant on OVH Cloud infrastructure.

## 📋 Prerequisites

- OVH Cloud account
- VPS or Public Cloud instance (minimum 2GB RAM recommended)
- SSH access to your server
- Domain name (optional, for custom URL)

## 🚀 Deployment Options

### Option 1: Docker Deployment (Recommended)

Docker provides the easiest and most reliable deployment method.

#### 1. Prepare Your OVH Server

```bash
# Connect to your OVH server
ssh your-user@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes to take effect
exit
ssh your-user@your-server-ip
```

#### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Create .env file
cp .env.example .env
nano .env  # Add your API keys
```

#### 3. Deploy with Docker Compose

```bash
# Start the application
docker-compose up -d

# Check logs
docker-compose logs -f

# Check status
docker-compose ps
```

#### 4. Configure Reverse Proxy (Nginx)

```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/ai-real-estate-assistant
```

Add this configuration:

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

        # WebSocket support
        proxy_read_timeout 86400;
    }
}
```

Enable the site:

```bash
# Enable configuration
sudo ln -s /etc/nginx/sites-available/ai-real-estate-assistant /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

#### 5. Set Up SSL (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

### Option 2: Systemd Service Deployment

For running without Docker using systemd.

#### 1. Prepare Server

```bash
# Connect to server
ssh your-user@your-server-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y
```

#### 2. Deploy Application

```bash
# Create application directory
sudo mkdir -p /opt/ai-real-estate-assistant
sudo chown $USER:$USER /opt/ai-real-estate-assistant

# Clone repository
cd /opt/ai-real-estate-assistant
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env  # Add your API keys
```

#### 3. Configure Systemd Service

```bash
# Copy service file
sudo cp ai-real-estate-assistant.service /etc/systemd/system/

# Edit service file if needed
sudo nano /etc/systemd/system/ai-real-estate-assistant.service

# Update paths and user if necessary
# User=your-user
# WorkingDirectory=/opt/ai-real-estate-assistant

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable ai-real-estate-assistant

# Start service
sudo systemctl start ai-real-estate-assistant

# Check status
sudo systemctl status ai-real-estate-assistant

# View logs
sudo journalctl -u ai-real-estate-assistant -f
```

#### 4. Configure Nginx (same as Docker option above)

---

## 🔒 Security Best Practices

### Firewall Configuration

```bash
# Install UFW (if not installed)
sudo apt install ufw -y

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Secure API Keys

```bash
# Ensure .env file is secure
chmod 600 .env

# Never commit .env to git
echo ".env" >> .gitignore
```

### Regular Updates

```bash
# For Docker deployment
cd /opt/ai-real-estate-assistant
git pull origin main
docker-compose down
docker-compose up -d --build

# For Systemd deployment
cd /opt/ai-real-estate-assistant
source venv/bin/activate
git pull origin main
pip install -r requirements.txt
sudo systemctl restart ai-real-estate-assistant
```

---

## 📊 Monitoring

### Check Application Health

```bash
# Docker
docker-compose ps
docker-compose logs -f ai-real-estate-assistant

# Systemd
sudo systemctl status ai-real-estate-assistant
sudo journalctl -u ai-real-estate-assistant -n 100
```

### Monitor Resources

```bash
# Install htop
sudo apt install htop -y

# Monitor resources
htop

# Check disk usage
df -h

# Check memory usage
free -h
```

---

## 🔄 Backup and Restore

### Backup Persistent Data

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backup/ai-real-estate-assistant"
APP_DIR="/opt/ai-real-estate-assistant"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database and preferences
tar -czf $BACKUP_DIR/data_$DATE.tar.gz \
    $APP_DIR/chroma_db \
    $APP_DIR/.preferences \
    $APP_DIR/.notifications \
    $APP_DIR/.sessions \
    $APP_DIR/.env

echo "Backup completed: $BACKUP_DIR/data_$DATE.tar.gz"
```

### Restore from Backup

```bash
# Extract backup
tar -xzf /backup/ai-real-estate-assistant/data_20250112_120000.tar.gz -C /

# Restart application
docker-compose restart  # For Docker
sudo systemctl restart ai-real-estate-assistant  # For Systemd
```

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8501
sudo lsof -i :8501

# Kill process if needed
sudo kill -9 <PID>
```

### Application Won't Start

```bash
# Check logs
docker-compose logs ai-real-estate-assistant  # Docker
sudo journalctl -u ai-real-estate-assistant -n 100  # Systemd

# Check environment variables
docker-compose config  # Docker
cat .env  # Verify API keys
```

### Memory Issues

```bash
# Check memory usage
free -h

# Increase swap if needed
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 📈 Scaling on OVH

### Vertical Scaling

Upgrade your VPS/Instance to a larger size through OVH Control Panel.

### Horizontal Scaling

Use OVH Load Balancer with multiple instances:

1. Deploy application on multiple instances
2. Configure OVH Load Balancer
3. Point load balancer to your instances
4. Use shared storage (e.g., OVH Object Storage) for ChromaDB

---

## 🌐 Custom Domain Setup

### OVH Domain Configuration

1. Go to OVH Control Panel
2. Select your domain
3. Add an A record pointing to your server IP
4. Configure SSL with Let's Encrypt (as shown above)

---

## 💰 Cost Optimization

- Use OVH VPS Starter (2GB RAM) for development: ~€5/month
- Use OVH VPS Comfort (4GB RAM) for production: ~€12/month
- Consider OVH Object Storage for large datasets: €0.01/GB/month
- Use OVH Load Balancer only if scaling to multiple instances: ~€10/month

---

## 📞 Support

For OVH-specific issues:
- OVH Support: https://help.ovhcloud.com/
- OVH Community: https://community.ovh.com/

For application issues:
- GitHub Issues: https://github.com/AleksNeStu/ai-real-estate-assistant/issues
- Documentation: See README.md and docs/

---

## ✅ Checklist

- [ ] OVH server provisioned and accessible
- [ ] Domain configured (if using custom domain)
- [ ] Application deployed (Docker or Systemd)
- [ ] Nginx reverse proxy configured
- [ ] SSL certificate obtained and configured
- [ ] Firewall configured
- [ ] .env file secured with API keys
- [ ] Backups configured
- [ ] Monitoring set up
- [ ] Application accessible and working

---

**Need Help?** Check the main [README.md](README.md) or create an [issue](https://github.com/AleksNeStu/ai-real-estate-assistant/issues).
