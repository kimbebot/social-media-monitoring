# 🏗️ Social Media Monitor - Architecture & Summary

## 📋 Project Overview

A production-ready, highly stealthy social media monitoring system designed to scrape posts from multiple platforms with maximum undetectability.

**Status**: ✅ **Ready for Deployment**

**Implemented Platforms**:
- ✅ LinkedIn (fully functional)
- 🔄 Facebook (template ready)
- 🔄 Twitter/X (template ready)

---

## 🎯 Key Features

### 🛡️ Maximum Stealth
- **Browser Fingerprinting**: Randomized viewports, user agents, timezone spoofing
- **Human Behavior**: Natural typing (8-15 chars/sec), random scrolling, mouse movements
- **Anti-Detection**: Removes webdriver flags, fakes plugins, randomizes canvas fingerprints
- **Session Management**: Cookie persistence, browser profile reuse
- **Smart Timing**: Random delays (2.5-7s), exponential backoff, non-uniform scheduling

### 🗄️ Database Architecture
- **Platforms**: Configuration for each social media platform
- **Accounts**: Encrypted credentials with session tracking
- **Posts**: Full post data with engagement metrics
- **Media**: Image/video attachments
- **Logs**: Execution history and error tracking

### ⚡ Performance
- **Async/Await**: Non-blocking I/O for concurrent scraping
- **Incremental Updates**: Only fetches new posts
- **Smart Deduplication**: Hash-based post identification
- **Session Reuse**: Minimizes login frequency

### 🔐 Security
- **Fernet Encryption**: All credentials encrypted at rest
- **No Plaintext Storage**: Passwords never stored in plain text
- **Secure Sessions**: Browser profiles encrypted
- **Environment Variables**: Sensitive config isolated

---

## 📁 Project Structure

```
social-monitor/
├── config/
│   └── settings.py              # Pydantic configuration
│
├── src/
│   ├── scrapers/
│   │   ├── base_scraper.py      # Abstract base class
│   │   └── linkedin_scraper.py  # LinkedIn implementation
│   │
│   ├── database/
│   │   ├── models.py            # SQLAlchemy models
│   │   └── db_manager.py        # Async database operations
│   │
│   ├── utils/
│   │   ├── stealth.py           # Anti-detection utilities
│   │   └── encryption.py        # Credential encryption
│   │
│   └── auth/
│       └── (future auth modules)
│
├── browser_profiles/            # Saved browser sessions
├── logs/                        # Application logs
├── data/                        # SQLite database
│
├── main.py                      # Main application
├── cli.py                       # Command-line interface
├── scheduler.py                 # Scheduled scraping
├── setup.sh                     # Installation script
│
├── .env.example                 # Environment template
├── requirements.txt             # Python dependencies
├── README.md                    # Full documentation
├── QUICKSTART.md               # Quick start guide
└── DEPLOYMENT.md               # VPS deployment guide
```

---

## 🔧 Technical Stack

### Core Technologies
- **Language**: Python 3.8+
- **Automation**: Playwright (Chrome/Chromium)
- **Database**: SQLAlchemy (SQLite/PostgreSQL)
- **Async**: asyncio, aiohttp
- **Scheduling**: APScheduler

### Key Libraries
- `playwright` - Browser automation
- `sqlalchemy` - ORM and database
- `cryptography` - Encryption (Fernet)
- `pydantic` - Configuration validation
- `loguru` - Enhanced logging
- `faker` - Random data generation

---

## 🎨 Architecture Patterns

### 1. **Base Scraper Pattern**

All platform scrapers inherit from `BaseScraper`:

```python
class BaseScraper(ABC):
    - initialize()
    - start_browser()
    - login()
    - verify_session()
    - scrape_feed()  # Abstract
    - save_posts()
    - cleanup()
```

Platform-specific scrapers only implement:
- `perform_login()` - Platform login flow
- `verify_session()` - Session validation
- `scrape_feed()` - Post extraction
- `get_base_url()` - Platform URL

### 2. **Stealth Layer**

```python
HumanBehavior:
    - random_delay()
    - human_type()
    - human_scroll()
    - random_mouse_movement()
    - occasional_pause()

StealthBrowser:
    - create_stealth_context()
    - _inject_stealth_scripts()

SessionManager:
    - save_session()
    - load_session()
```

### 3. **Database Layer**

```python
DatabaseManager:
    - get_or_create_platform()
    - create_account()
    - create_post()
    - bulk_create_posts()
    - create_scraper_log()
```

All operations are async and context-managed.

---

## 🔄 Execution Flow

### 1. **Initialization**
```
main.py
  ↓
SocialMediaMonitor.initialize()
  ↓
db.init_db() + Load scrapers
```

### 2. **Scraping Flow**
```
scraper.run(username, password)
  ↓
initialize() → start_browser() → login()
  ↓
load_session() OR perform_login()
  ↓
scrape_feed() → extract posts
  ↓
save_posts() → db.bulk_create_posts()
  ↓
cleanup() → close browser
```

### 3. **Scheduled Execution**
```
scheduler.py
  ↓
Get all active accounts
  ↓
For each account:
  - Random delay (1-5 min)
  - Run scraper
  - Delay between accounts (5-10 min)
  ↓
Reschedule with random interval (2.5-3.5 hours)
```

---

## 🎯 Stealth Techniques Explained

### Browser Fingerprinting
```javascript
// Remove automation detection
navigator.webdriver = undefined

// Fake plugins
navigator.plugins = [Chrome PDF Plugin, ...]

// Randomize canvas
getImageData() → add noise

// Chrome runtime
window.chrome = { runtime: {} }
```

### Human Behavior Simulation
```python
# Typing: 50-150ms per character
await element.type(char, delay=random.randint(50, 150))

# Scrolling: Variable distances + pauses
scroll_amount = random(viewport * 0.3, viewport * 0.8)
await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
await delay(1.5, 4.0)

# Random pauses: Simulate "thinking"
if random() < 0.15:
    await sleep(random(3.0, 8.0))
```

### Session Management
```python
# First login
perform_login() → save cookies/storage → SessionManager.save()

# Subsequent runs
load_session() → verify_session() → skip login if valid
```

---

## 📊 Database Schema

### Platforms
```sql
- id (PK)
- name (linkedin, facebook, twitter)
- base_url
- is_active
- last_scraped_at
```

### Accounts
```sql
- id (PK)
- platform_id (FK)
- username
- email
- password_encrypted (Fernet)
- session_valid
- cookies_data (JSON)
```

### Posts
```sql
- id (PK)
- platform_id (FK)
- external_id (platform's post ID)
- author_name, author_username
- content, content_html
- posted_at, scraped_at
- likes_count, comments_count, shares_count
- raw_data (JSON)
```

### Media
```sql
- id (PK)
- post_id (FK)
- media_type (image/video/gif)
- media_url, thumbnail_url
- width, height, duration
```

---

## 🚀 Deployment Strategies

### Local Development
```bash
# Non-headless for debugging
HEADLESS=false python3 cli.py scrape linkedin user pass --no-headless
```

### VPS Production
```bash
# Headless with systemd
sudo systemctl start social-monitor

# With proxies
USE_PROXY=true
PROXY_URL=http://proxy:port
```

### Docker (Future)
```dockerfile
FROM python:3.11-slim
RUN playwright install chromium --with-deps
COPY . /app
CMD ["python3", "scheduler.py"]
```

---

## 🔍 Monitoring & Debugging

### Logs
```bash
# Application logs
tail -f logs/social_monitor.log

# Systemd logs
journalctl -u social-monitor -f
```

### CLI Tools
```bash
# Stats
python3 cli.py stats

# Recent posts
python3 cli.py list-posts linkedin 20

# Account status
python3 cli.py list-accounts
```

### Database Queries
```python
# Direct SQL
async with db.get_session() as session:
    result = await session.execute(select(Post).where(...))
```

---

## 🎓 Best Practices

### Stealth
1. ✅ Always use random delays
2. ✅ Rotate user agents
3. ✅ Use residential proxies on VPS
4. ✅ Start with long intervals (4+ hours)
5. ✅ Mimic human patterns

### Security
1. ✅ Encrypt all credentials
2. ✅ Use .env for configuration
3. ✅ Never commit .env to git
4. ✅ Rotate encryption keys periodically
5. ✅ Use VPN + proxy in production

### Reliability
1. ✅ Implement exponential backoff
2. ✅ Log all errors
3. ✅ Validate sessions before scraping
4. ✅ Handle network failures gracefully
5. ✅ Backup database regularly

---

## 🛣️ Roadmap

### Phase 1: ✅ Core (Completed)
- [x] Base scraper architecture
- [x] LinkedIn scraper
- [x] Database models
- [x] Stealth utilities
- [x] CLI interface
- [x] Scheduling system

### Phase 2: 🔄 Platform Expansion
- [ ] Facebook scraper
- [ ] Twitter/X scraper
- [ ] Instagram scraper
- [ ] Reddit scraper

### Phase 3: 🔄 Features
- [ ] Webhook notifications
- [ ] Web dashboard
- [ ] Export to CSV/JSON
- [ ] Advanced filtering
- [ ] Sentiment analysis

### Phase 4: 🔄 Infrastructure
- [ ] Docker support
- [ ] Proxy rotation
- [ ] Multi-account load balancing
- [ ] Cloud deployment (AWS/GCP)

---

## 📖 Key Files

| File | Purpose |
|------|---------|
| `main.py` | Main application entry point |
| `cli.py` | Command-line interface |
| `scheduler.py` | Scheduled execution |
| `src/scrapers/base_scraper.py` | Abstract base scraper |
| `src/utils/stealth.py` | Anti-detection utilities |
| `src/database/models.py` | Database schema |
| `config/settings.py` | Configuration management |
| `QUICKSTART.md` | Quick start guide |
| `DEPLOYMENT.md` | VPS deployment guide |

---

## 🎉 Getting Started

1. **Install**: `./setup.sh`
2. **Configure**: Edit `.env`
3. **Add Account**: `python3 cli.py add-account ...`
4. **Test**: `python3 cli.py scrape ... --no-headless`
5. **Deploy**: `python3 scheduler.py`

---

## 📞 Support

- Check logs: `logs/social_monitor.log`
- Database issues: Delete and reinitialize
- Session expired: Remove `browser_profiles/*`
- Login fails: Use `--no-headless` mode

---

**Built with maximum stealth in mind** 🥷
