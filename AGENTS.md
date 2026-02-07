# 🤖 AGENTS.md - System Actors & Components

This document explains all the "agents" (actors/components) in the Social Media Monitor system and how they interact.

---

## 🎭 What Are "Agents" in This System?

In this project, "agents" refers to the different autonomous components that work together:
- **Scrapers** - The bots that pretend to be human users
- **Database Manager** - Handles all data storage/retrieval
- **Scheduler** - Orchestrates when scrapers run
- **Session Manager** - Maintains login sessions
- **Stealth Engine** - Makes everything undetectable

---

## 📊 System Architecture Map

```
┌─────────────────────────────────────────────────────────────┐
│                     USER (You)                               │
│                         ↓                                    │
│              ┌──────────────────────┐                        │
│              │   CLI Interface      │                        │
│              │   (cli.py)           │                        │
│              └──────────────────────┘                        │
│                         ↓                                    │
│              ┌──────────────────────┐                        │
│              │  Main Orchestrator   │                        │
│              │  (main.py)           │                        │
│              └──────────────────────┘                        │
│                         ↓                                    │
│       ┌─────────────────┴─────────────────┐                 │
│       ↓                                    ↓                 │
│  ┌─────────────┐                   ┌─────────────┐          │
│  │  Scheduler  │                   │  Scraper    │          │
│  │  Agent      │ ←────triggers───→ │  Agents     │          │
│  └─────────────┘                   └─────────────┘          │
│                                            ↓                 │
│                                    ┌──────────────┐          │
│                                    │ Stealth      │          │
│                                    │ Engine       │          │
│                                    └──────────────┘          │
│                                            ↓                 │
│                                    ┌──────────────┐          │
│                                    │ Session      │          │
│                                    │ Manager      │          │
│                                    └──────────────┘          │
│                                            ↓                 │
│                                    ┌──────────────┐          │
│                                    │ Browser      │          │
│                                    │ (Playwright) │          │
│                                    └──────────────┘          │
│                                            ↓                 │
│                               ┌─────────────────────┐        │
│                               │  Social Media       │        │
│                               │  Platforms          │        │
│                               │  (LinkedIn, etc)    │        │
│                               └─────────────────────┘        │
│                                            ↓                 │
│                               ┌─────────────────────┐        │
│                               │  Database Manager   │        │
│                               │  (Stores Posts)     │        │
│                               └─────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Breakdown

### 1. **CLI Agent** (`cli.py`)
**Role:** Command interface for humans  
**Responsibilities:**
- Accept user commands
- Add/manage accounts
- Trigger manual scrapes
- Display statistics and posts
- Export data

**Key Functions:**
```python
add-account      # Add new social media account
list-accounts    # Show all accounts
scrape          # Run scraper manually
list-posts      # View scraped posts
stats           # Show system statistics
```

**Interactions:**
- → Database Manager (read/write accounts, posts)
- → Main Orchestrator (trigger scrapes)

---

### 2. **Main Orchestrator** (`main.py`)
**Role:** Central coordinator  
**Responsibilities:**
- Initialize all components
- Manage scraper lifecycle
- Route commands from CLI
- Handle errors globally
- Coordinate multi-platform scraping

**Key Components:**
```python
SocialMediaMonitor
  - initialize()        # Boot up system
  - run_scraper()       # Execute single scraper
  - run_all_scrapers()  # Execute all platforms
```

**Interactions:**
- ← CLI Agent (receives commands)
- → Scraper Agents (spawns and manages)
- → Database Manager (init and coordination)

---

### 3. **Scheduler Agent** (`scheduler.py`)
**Role:** Automated timing controller  
**Responsibilities:**
- Run scrapers on schedule
- Randomize intervals (stealth)
- Add delays between accounts
- Handle rescheduling
- Manage concurrent scraping

**Intelligence:**
- **Random intervals:** 2.5-3.5 hours (not predictable)
- **Account delays:** 5-10 minutes between accounts
- **Platform delays:** Spacing between platforms
- **Self-rescheduling:** New random interval after each run

**Key Functions:**
```python
ScheduledMonitor
  - scrape_all_platforms()  # Main job
  - scrape_account()        # Single account job
  - add_jobs()              # Schedule setup
  - _on_job_executed()      # Reschedule with randomness
```

**Interactions:**
- → Main Orchestrator (triggers scrapes)
- → Scraper Agents (spawns with delays)
- Uses APScheduler internally

---

### 4. **Scraper Agents** (Platform-Specific)

Each platform has its own scraper agent:

#### **Base Scraper** (`base_scraper.py`)
**Role:** Abstract parent class  
**Provides:**
- Browser lifecycle management
- Login orchestration
- Session handling
- Post saving logic
- Error handling
- Logging

**Template Methods (implemented by children):**
```python
perform_login()      # Platform-specific login
verify_session()     # Check if session valid
scrape_feed()        # Extract posts
get_base_url()       # Platform URL
```

#### **LinkedIn Scraper Agent** (`linkedin_scraper.py`)
**Role:** LinkedIn-specific implementation  
**Responsibilities:**
- Navigate LinkedIn feed
- Extract post data (author, content, engagement)
- Handle LinkedIn's HTML structure
- Parse relative timestamps
- Extract media attachments

**Stealth Features:**
- Mimics human scrolling
- Random pauses between posts
- Natural typing for login
- Session reuse

**Output:**
```python
{
  'external_id': 'post_123',
  'author_name': 'John Doe',
  'content': 'Post text...',
  'likes_count': 42,
  'posted_at': datetime,
  # ... more fields
}
```

#### **Future Scraper Agents**
- `facebook_scraper.py` - Facebook implementation
- `twitter_scraper.py` - Twitter/X implementation
- `instagram_scraper.py` - Instagram implementation

---

### 5. **Stealth Engine** (`stealth.py`)
**Role:** Anti-detection system  
**Responsibilities:**
- Make automation undetectable
- Simulate human behavior
- Randomize browser fingerprints
- Manage timing patterns

**Sub-Components:**

#### **HumanBehavior Class**
Simulates realistic user actions:
```python
random_delay()           # 2.5-7 second pauses
human_type()             # Natural typing speed
human_scroll()           # Realistic scrolling
random_mouse_movement()  # Mouse movements
occasional_pause()       # "Thinking" pauses
```

#### **StealthBrowser Class**
Creates undetectable browser contexts:
```python
create_stealth_context()     # Setup stealth browser
_inject_stealth_scripts()    # Remove automation flags
```

**Stealth Techniques:**
- Remove `navigator.webdriver`
- Fake browser plugins
- Randomize canvas fingerprints
- Spoof Chrome runtime
- Random viewport sizes
- Rotating user agents

#### **StealthConfig Class**
Configuration for stealth parameters:
```python
TYPING_SPEED_MIN/MAX     # 8-15 chars/sec
VIEWPORTS                # Common screen sizes
USER_AGENTS              # Real browser signatures
```

---

### 6. **Session Manager** (`stealth.py`)
**Role:** Login session persistence  
**Responsibilities:**
- Save browser sessions (cookies, storage)
- Load existing sessions
- Validate session freshness
- Minimize login frequency (stealth!)

**Key Functions:**
```python
save_session()    # Save after successful login
load_session()    # Restore previous session
```

**Storage:**
- Cookies saved to `browser_profiles/`
- Per-platform, per-account files
- JSON format with full browser state

**Benefit:**
- Login once, reuse for weeks
- Avoids suspicious frequent logins
- Faster execution

---

### 7. **Database Manager** (`db_manager.py`)
**Role:** Data persistence layer  
**Responsibilities:**
- Store/retrieve all data
- Handle deduplication
- Manage relationships
- Transaction management
- Async operations

**Key Operations:**
```python
# Platforms
get_or_create_platform()
get_active_platforms()

# Accounts
create_account()
get_account()
update_account_session()

# Posts
create_post()               # Single post
bulk_create_posts()         # Multiple posts (deduped)
get_latest_post_date()      # For incremental scraping

# Logging
create_scraper_log()
update_scraper_log()
```

**Data Models:**
- **Platform** - Social media sites
- **Account** - User credentials (encrypted)
- **Post** - Scraped posts with metadata
- **Media** - Images/videos attached to posts
- **ScraperLog** - Execution history

**Intelligence:**
- Automatic deduplication (checks external_id)
- Bulk operations for efficiency
- Async for non-blocking I/O

---

### 8. **Encryption Agent** (`encryption.py`)
**Role:** Security & credential protection  
**Responsibilities:**
- Encrypt passwords before storage
- Decrypt passwords for use
- Key management
- Secure data at rest

**Implementation:**
```python
encrypt(plaintext)    # Password → encrypted
decrypt(encrypted)    # Encrypted → password
generate_key()        # Create new Fernet key
```

**Security:**
- Fernet symmetric encryption
- Keys stored in `.env` (never in code)
- No plaintext passwords anywhere

---

### 9. **Browser Agent** (Playwright)
**Role:** Headless browser automation  
**Responsibilities:**
- Render web pages
- Execute JavaScript
- Handle navigation
- Manage cookies
- Simulate user interactions

**Not written by us** - provided by Playwright library

**Controlled By:**
- Stealth Engine (fingerprinting)
- Scraper Agents (navigation)
- Session Manager (cookies)

---

## 🔄 Agent Interaction Flows

### **Flow 1: Manual Scrape**
```
User
  ↓ (command)
CLI Agent
  ↓ (parse command)
Main Orchestrator
  ↓ (spawn)
LinkedIn Scraper Agent
  ↓ (initialize)
Stealth Engine → Browser Agent
  ↓ (navigate)
Session Manager → Browser Agent
  ↓ (load cookies)
Browser Agent → LinkedIn.com
  ↓ (scrape HTML)
LinkedIn Scraper Agent
  ↓ (extract data)
Database Manager
  ↓ (save posts)
SQLite/PostgreSQL
```

### **Flow 2: Scheduled Scrape**
```
Scheduler Agent (timer fires)
  ↓ (trigger)
Main Orchestrator
  ↓ (for each account)
Random Delay (1-5 min)
  ↓
LinkedIn Scraper Agent
  ↓
[Same as Flow 1]
  ↓
Delay Between Accounts (5-10 min)
  ↓
Next Account...
  ↓
Scheduler Agent (reschedule with new random interval)
```

### **Flow 3: First Login**
```
Scraper Agent
  ↓
Session Manager (no session found)
  ↓
Stealth Engine (create stealth browser)
  ↓
Browser Agent (navigate to login page)
  ↓
HumanBehavior (type username slowly)
  ↓
HumanBehavior (type password naturally)
  ↓
Random Delay (1-2 sec)
  ↓
Browser Agent (click submit)
  ↓
Wait for navigation...
  ↓
Session Manager (save cookies)
  ↓
Database Manager (update account session)
  ↓
Scraper Agent (proceed to scrape)
```

### **Flow 4: Subsequent Login (Session Reuse)**
```
Scraper Agent
  ↓
Session Manager (session found!)
  ↓
Stealth Engine (create browser)
  ↓
Browser Agent (load cookies)
  ↓
Browser Agent (navigate to feed)
  ↓
Verify session still valid
  ↓
Scraper Agent (proceed to scrape)
  ↓
[No login needed! Stealth win!]
```

---

## 🧠 Intelligence & Autonomy

### **Which Agents Are "Smart"?**

| Agent | Intelligence Level | Autonomous? |
|-------|-------------------|-------------|
| Scheduler | ⭐⭐⭐ High | ✅ Yes - self-rescheduling |
| Scraper Agents | ⭐⭐⭐ High | ✅ Yes - navigate & extract |
| Stealth Engine | ⭐⭐ Medium | ⚠️ Semi - rule-based randomness |
| Session Manager | ⭐⭐ Medium | ✅ Yes - decides to reuse/refresh |
| Database Manager | ⭐ Low | ❌ No - passive storage |
| CLI Agent | ⭐ Low | ❌ No - awaits user input |
| Encryption Agent | ⭐ Low | ❌ No - utility only |

### **Adaptive Behaviors**

**Scheduler Agent:**
- Adjusts intervals randomly
- Spreads out account scraping
- Reschedules on errors

**Scraper Agents:**
- Detect session expiration
- Handle dynamic content loading
- Adapt to HTML structure changes (via selectors)
- Skip already-scraped posts

**Session Manager:**
- Validates session before reuse
- Falls back to fresh login if stale

**Stealth Engine:**
- Randomizes all timing
- Varies scroll distances
- Adds "thinking" pauses randomly

---

## 🎮 Control & Coordination

### **Who Controls What?**

**Main Orchestrator:**
- Overall system lifecycle
- Spawning scraper agents
- Error recovery

**Scheduler Agent:**
- Timing of automated scrapes
- Concurrency control
- Rescheduling logic

**Scraper Agents:**
- Their own execution flow
- When to scroll, type, click
- What data to extract

**Database Manager:**
- Data consistency
- Transaction boundaries
- Deduplication logic

---

## 🔧 Extending the System

### **Adding a New Platform Agent**

1. Create `src/scrapers/facebook_scraper.py`
2. Inherit from `BaseScraper`
3. Implement 4 methods:
   ```python
   perform_login()      # FB-specific login
   verify_session()     # Check FB session
   scrape_feed()        # Extract FB posts
   get_base_url()       # return "https://facebook.com"
   ```
4. Add to `main.py`:
   ```python
   if settings.facebook_enabled:
       self.scrapers['facebook'] = FacebookScraper()
   ```

### **Adding a New Behavior to Stealth Engine**

```python
# In HumanBehavior class
@staticmethod
async def random_click_away():
    """Simulate accidental clicks"""
    if random.random() < 0.05:  # 5% chance
        # Click random spot
        # Immediate back navigation
        pass
```

---

## 🎯 Design Principles

### **Separation of Concerns**
Each agent has ONE job:
- Scrapers scrape
- Database stores
- Stealth hides
- Scheduler schedules

### **Composition Over Inheritance**
- Base scraper provides framework
- Platform scrapers add specifics
- Stealth is injected, not inherited

### **Async Everything**
All agents use async/await:
- Non-blocking I/O
- Concurrent operations
- Better resource usage

### **Fail Gracefully**
Each agent handles its own errors:
- Scrapers log and skip bad posts
- Database rolls back on errors
- Scheduler reschedules on failures

---

## 📊 Agent Communication

### **Direct Calls**
```python
# Scraper → Database
await db.create_post(post_data)

# Scraper → Stealth
await HumanBehavior.random_delay()
```

### **Event-Based**
```python
# Scheduler → APScheduler events
scheduler.add_listener(on_job_executed)
```

### **Shared State**
```python
# Configuration (settings.py)
settings.headless
settings.scrape_interval

# Database (db_manager.py)
db.get_session()
```

---

## 🎓 Key Takeaways

1. **Modularity:** Each agent is independent and testable
2. **Stealth by Design:** Randomness at every layer
3. **Session Reuse:** Huge stealth win, built into Session Manager
4. **Async Architecture:** All agents can run concurrently
5. **Extensible:** Add platforms without touching core
6. **Fail-Safe:** Each agent handles its own errors
7. **Intelligent Scheduling:** Not just cron - adaptive timing

---

## 🚀 Future Agent Possibilities

### **Monitoring Agent**
- Watch for bans/blocks
- Alert on suspicious activity
- Auto-pause if detected

### **Proxy Rotation Agent**
- Manage proxy pool
- Rotate IPs intelligently
- Test proxy health

### **Analysis Agent**
- Sentiment analysis on posts
- Trend detection
- Engagement predictions

### **Notification Agent**
- Webhooks for new posts
- Email digests
- Slack/Discord integration

---