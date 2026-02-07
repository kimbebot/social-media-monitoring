# 🚀 Quick Start Guide

Get up and running with Social Media Monitor in 5 minutes.

## ⚡ Super Quick Start

```bash
# 1. Setup
./setup.sh

# 2. Add your account
python3 -c "
import asyncio
from main import add_account
asyncio.run(add_account(
    'linkedin',
    'your_email@example.com',
    'your_email@example.com',
    'your_password'
))
"

# 3. Test (non-headless first time for 2FA/CAPTCHA)
python3 cli.py scrape linkedin your_email@example.com your_password --no-headless

# 4. View results
python3 cli.py list-posts linkedin 10
```

## 📝 Step-by-Step

### 1. Installation (2 minutes)

```bash
# Automatic
./setup.sh

# Manual
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

### 2. Generate Encryption Key

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy output to .env file: ENCRYPTION_KEY=...
```

### 3. Add Account

```bash
# Using CLI
python3 cli.py add-account linkedin user@email.com user@email.com mypassword

# OR using Python
python3 -c "
import asyncio
from main import add_account
asyncio.run(add_account('linkedin', 'user@email.com', 'user@email.com', 'mypass'))
"
```

### 4. First Run (Non-Headless)

**IMPORTANT**: First login should be in visible browser to handle:
- 2FA verification
- CAPTCHA
- Security challenges

```bash
python3 cli.py scrape linkedin user@email.com mypassword --no-headless
```

Watch the browser, complete any challenges, then session will be saved!

### 5. View Results

```bash
# List scraped posts
python3 cli.py list-posts linkedin 20

# View stats
python3 cli.py stats

# View accounts
python3 cli.py list-accounts
```

## 🔄 Continuous Monitoring

### Run Once

```bash
python3 main.py
```

### Run on Schedule

```bash
# Runs continuously with smart random intervals
python3 scheduler.py
```

### Production Deployment

```bash
# Using systemd (recommended for VPS)
sudo systemctl start social-monitor

# Using screen
screen -S monitor
python3 scheduler.py
# Press Ctrl+A then D to detach
```

## 🎯 Common Tasks

### Add Multiple Accounts

```python
# create_accounts.py
import asyncio
from main import add_account

async def setup():
    await add_account('linkedin', 'user1@email.com', 'user1@email.com', 'pass1')
    await add_account('linkedin', 'user2@email.com', 'user2@email.com', 'pass2')
    # await add_account('facebook', 'user@email.com', 'user@email.com', 'pass')

asyncio.run(setup())
```

```bash
python3 create_accounts.py
```

### Query Database

```python
# query_posts.py
import asyncio
from src.database.db_manager import db
from sqlalchemy import select
from src.database.models import Post

async def get_posts():
    await db.init_db()
    async with db.get_session() as session:
        result = await session.execute(
            select(Post)
            .order_by(Post.posted_at.desc())
            .limit(20)
        )
        posts = result.scalars().all()
        for post in posts:
            print(f"{post.author_name}: {post.content[:100]}")

asyncio.run(get_posts())
```

### Export to CSV

```python
# export_csv.py
import asyncio
import csv
from src.database.db_manager import db
from sqlalchemy import select
from src.database.models import Post

async def export():
    await db.init_db()
    async with db.get_session() as session:
        result = await session.execute(select(Post))
        posts = result.scalars().all()
        
        with open('posts.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Author', 'Content', 'Posted At', 'Likes', 'URL'])
            for post in posts:
                writer.writerow([
                    post.author_name,
                    post.content,
                    post.posted_at,
                    post.likes_count,
                    post.post_url
                ])

asyncio.run(export())
```

## ⚙️ Configuration

### Essential .env Settings

```env
# Display browser (for debugging)
HEADLESS=false

# Hide browser (for production)
HEADLESS=true

# Scraping delays
MIN_DELAY=2.5      # Minimum seconds between actions
MAX_DELAY=7.0      # Maximum seconds

# Interval between scrapes
SCRAPE_INTERVAL_MINUTES=180  # 3 hours

# Use proxy (recommended for VPS)
USE_PROXY=true
PROXY_URL=http://user:pass@proxy.com:8080
```

## 🐛 Troubleshooting

### Login Fails

```bash
# Run in visible mode
python3 cli.py scrape linkedin user@email.com pass --no-headless

# Check logs
tail -f logs/social_monitor.log
```

### No Posts Scraped

1. Check if session is valid: `python3 cli.py list-accounts`
2. Delete old session: `rm -rf browser_profiles/*`
3. Re-login in non-headless mode

### Session Expired

```bash
# Delete session files
rm -rf browser_profiles/*

# Re-authenticate
python3 cli.py scrape linkedin user@email.com pass --no-headless
```

## 📚 Next Steps

1. ✅ Read full [README.md](README.md)
2. ✅ Check [DEPLOYMENT.md](DEPLOYMENT.md) for VPS setup
3. ✅ Implement Facebook scraper (copy LinkedIn template)
4. ✅ Set up scheduled monitoring
5. ✅ Configure proxy for stealth

## 💡 Tips

- **First time**: Always use `--no-headless` to handle 2FA
- **Sessions**: Last 7-30 days typically
- **Proxies**: Essential for VPS deployment
- **Intervals**: Start with 4-6 hours, adjust based on bans
- **Backups**: Backup database weekly

## 🆘 Help

```bash
# CLI help
python3 cli.py help

# View logs
tail -f logs/social_monitor.log

# Check status
python3 cli.py stats
```

---

**Ready to monitor!** 🎉

Need more features? Check templates for Facebook and Twitter scrapers in `src/scrapers/`
