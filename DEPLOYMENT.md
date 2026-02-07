# 🚀 VPS Deployment Guide

Complete guide for deploying Social Media Monitor on a VPS with maximum stealth.

## 📋 Prerequisites

- Ubuntu 20.04+ or Debian 11+ VPS
- Minimum 1GB RAM, 2GB recommended
- Python 3.8+
- SSH access to VPS

## 🔧 VPS Setup

### 1. Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv git wget curl

# Install system dependencies for Playwright
sudo apt install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2
```

### 2. Security Hardening

```bash
# Create non-root user
sudo adduser scraper
sudo usermod -aG sudo scraper

# Switch to new user
su - scraper

# Set up SSH key authentication (recommended)
mkdir -p ~/.ssh
chmod 700 ~/.ssh
# Copy your public key to ~/.ssh/authorized_keys

# Disable password authentication (after SSH key is working)
# sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# sudo systemctl restart sshd
```

### 3. Install Project

```bash
# Clone or upload project
cd ~
git clone <your-repo> social-monitor
# OR
scp -r social-monitor user@your-vps:~/

cd ~/social-monitor
```

### 4. Configure Environment

```bash
# Run setup
./setup.sh

# Edit configuration
nano .env
```

Important `.env` settings for VPS:
```env
# Use headless mode on VPS
HEADLESS=true

# Set appropriate log level
LOG_LEVEL=INFO

# Database (use PostgreSQL for production)
DATABASE_URL=sqlite+aiosqlite:///./data/social_monitor.db
# Or PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/social_monitor

# Use proxy for extra stealth
USE_PROXY=true
PROXY_URL=http://user:pass@proxy-server:port

# Longer intervals for VPS
SCRAPE_INTERVAL_MINUTES=240  # 4 hours
```

## 🔐 Proxy Setup (Recommended)

### Option 1: Residential Proxy Services

Purchase from providers like:
- Bright Data (expensive but reliable)
- Smartproxy
- Oxylabs
- IPRoyal

Add to `.env`:
```env
USE_PROXY=true
PROXY_URL=http://username:password@gate.smartproxy.com:7000
```

### Option 2: SOCKS5 Proxy

```bash
# Install Dante (SOCKS5 server)
sudo apt install dante-server

# Configure /etc/danted.conf
# Then start: sudo systemctl start danted
```

## 🚀 Running as Service

### Option 1: Systemd Service (Recommended)

Create service file:
```bash
sudo nano /etc/systemd/system/social-monitor.service
```

Add content:
```ini
[Unit]
Description=Social Media Monitor
After=network.target

[Service]
Type=simple
User=scraper
WorkingDirectory=/home/scraper/social-monitor
Environment="PATH=/home/scraper/social-monitor/venv/bin"
ExecStart=/home/scraper/social-monitor/venv/bin/python3 scheduler.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable social-monitor
sudo systemctl start social-monitor

# Check status
sudo systemctl status social-monitor

# View logs
sudo journalctl -u social-monitor -f
```

### Option 2: Screen/Tmux (Simple)

```bash
# Install screen
sudo apt install screen

# Start in screen session
screen -S monitor
cd ~/social-monitor
source venv/bin/activate
python3 scheduler.py

# Detach: Ctrl+A then D
# Reattach: screen -r monitor
```

### Option 3: Supervisor

```bash
# Install supervisor
sudo apt install supervisor

# Create config
sudo nano /etc/supervisor/conf.d/social-monitor.conf
```

```ini
[program:social-monitor]
command=/home/scraper/social-monitor/venv/bin/python3 scheduler.py
directory=/home/scraper/social-monitor
user=scraper
autostart=true
autorestart=true
stderr_logfile=/var/log/social-monitor.err.log
stdout_logfile=/var/log/social-monitor.out.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start social-monitor
```

## 📊 Monitoring

### View Logs

```bash
# Application logs
tail -f ~/social-monitor/logs/social_monitor.log

# Systemd logs
sudo journalctl -u social-monitor -f --lines=100

# Check stats
cd ~/social-monitor
source venv/bin/activate
python3 cli.py stats
```

### Set Up Log Rotation

```bash
sudo nano /etc/logrotate.d/social-monitor
```

```
/home/scraper/social-monitor/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

## 🛡️ Additional Security

### 1. VPN Setup (Optional)

```bash
# Install OpenVPN
sudo apt install openvpn

# Add provider config
sudo cp your-vpn-config.ovpn /etc/openvpn/client.conf
sudo systemctl start openvpn@client
sudo systemctl enable openvpn@client
```

### 2. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### 3. Fail2Ban (Prevent SSH attacks)

```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## 🔄 Database Backups

### Automated Backups

```bash
# Create backup script
nano ~/backup-db.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/scraper/backups"
mkdir -p $BACKUP_DIR

# Backup SQLite
cp ~/social-monitor/data/social_monitor.db $BACKUP_DIR/social_monitor_$DATE.db

# Keep only last 7 days
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x ~/backup-db.sh

# Add to crontab (daily at 3 AM)
crontab -e
# Add: 0 3 * * * /home/scraper/backup-db.sh
```

## 📈 Performance Tuning

### PostgreSQL (If using)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres psql
CREATE DATABASE social_monitor;
CREATE USER scraper WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE social_monitor TO scraper;
\q

# Update .env
DATABASE_URL=postgresql+asyncpg://scraper:your_password@localhost/social_monitor
```

## 🔍 Troubleshooting

### Check Running Processes

```bash
ps aux | grep python3
htop
```

### Kill Stuck Process

```bash
sudo systemctl stop social-monitor
# or
pkill -f scheduler.py
```

### View Browser Processes

```bash
ps aux | grep chromium
```

### Cleanup Old Sessions

```bash
cd ~/social-monitor
rm -rf browser_profiles/*
```

## 📱 Remote Access

### SSH Tunnel (Secure Database Access)

```bash
# From local machine
ssh -L 5432:localhost:5432 user@your-vps

# Now you can connect to localhost:5432
```

## 🔄 Updates

### Update Application

```bash
cd ~/social-monitor
git pull origin main  # or upload new files
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart service
sudo systemctl restart social-monitor
```

## ⚠️ Important Notes

1. **First Run**: Use `--no-headless` mode locally first to handle any login challenges
2. **Sessions**: Copy `browser_profiles/` to VPS after successful local login
3. **Proxies**: Essential for avoiding IP bans on VPS
4. **Monitoring**: Check logs daily for first week
5. **Backups**: Always backup before updates

## 📊 Resource Usage

Typical usage:
- **RAM**: 200-500 MB per scraper instance
- **CPU**: Low (5-10% average)
- **Storage**: 100MB + ~1GB per month of posts
- **Network**: Minimal (<1GB/month typically)

## 🎯 Best Practices

1. ✅ Use residential proxies
2. ✅ Run during random times
3. ✅ Start with long intervals (4-6 hours)
4. ✅ Monitor for bans daily
5. ✅ Keep backup accounts ready
6. ✅ Use VPN + Proxy for maximum stealth
7. ✅ Regularly update user agents
8. ✅ Don't scrape too frequently

---

**Need Help?** Check logs first: `tail -f ~/social-monitor/logs/social_monitor.log`
