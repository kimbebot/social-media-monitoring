# Social Media Monitor

## Overview
Social Media Monitor is a FastAPI-backed social monitoring app with a browser automation frontend. It tracks active monitored URLs, scrapes new posts from supported social platforms, stores results in a database, and exposes a web UI for managing platforms, accounts, monitored URLs, and scrape runs.

The current codebase supports LinkedIn, Facebook, Instagram, and X. LinkedIn is implemented through both company-page scraping and feed scraping, while Facebook, Instagram, and X have platform-specific scrapers and session handling. The app also exports new results to Excel.

## Applications and Services

### Web UI and API Server
- Description: Serves the browser-based dashboard and exposes the REST API and WebSocket feed used by the UI.
- Main responsibilities: Manage platforms, accounts, monitored URLs, settings, scraping runs, live progress, and Excel export.
- Key technologies: FastAPI, WebSocket, OpenPyXL, Pydantic.
- Important entry point: `app/api_server.py`.
- Important files and folders: `web/index.html`, `web/app.js`, `web/styles.css`, `web/images/`.
- Environment variables: `DATABASE_URL`, `ENCRYPTION_KEY`, `HEADLESS`, `RUN_PARALLEL`, `USE_PROXY`, `PROXY_URL`, `USER_DATA_DIR`, `LOG_LEVEL`, `LOG_FILE`.
- How to run it: `./start.sh` after activating `.venv`, or `uvicorn app.api_server:app --reload`.
- How to test it: Start the server and exercise the UI or call the API endpoints directly.
- Notes for future developers: The UI state is driven by `/api/platforms`, `/api/settings`, and `/api/monitored-urls`. Platform toggles are persisted in the `platforms` table.

### CLI
- Description: Minimal command-line interface for listing accounts, listing posts, scraping a single account, and printing stats.
- Main responsibilities: Manual inspection and one-off runs without the web UI.
- Key technologies: argparse-style `sys.argv` handling, asyncio, SQLAlchemy.
- Important entry point: `app/cli.py`.
- Environment variables: Same app settings as the API server, loaded from `.env`.
- How to run it: `python3 app/cli.py help`.
- How to test it: Use `list-accounts`, `list-posts`, `stats`, and `scrape` against a known account.
- Notes for future developers: The CLI still expects account credentials as arguments for direct scraping, while scheduled runs use database-backed accounts.

### Main Orchestrator
- Description: Bootstraps the database and registered scrapers.
- Main responsibilities: Initialize application state, register enabled scrapers, and coordinate scraper execution.
- Key technologies: asyncio, Loguru.
- Important entry point: `app/main.py`.
- Environment variables: `LINKEDIN_ENABLED`, `FACEBOOK_ENABLED`, `TWITTER_ENABLED` are still present in settings, though the web UI now controls platform activation via the database.
- How to run it: `python3 app/main.py`.
- How to test it: Confirm the expected scraper is registered and initialization succeeds.
- Notes for future developers: `run_all_scrapers()` is currently a scaffold and does not yet contain complete per-account orchestration.

### Scheduler
- Description: Runs scraping on a randomized interval.
- Main responsibilities: Schedule repeated scraping jobs, delay between accounts, and reschedule after each run.
- Key technologies: APScheduler, asyncio.
- Important entry point: `app/scheduler.py`.
- Environment variables: `SCRAPE_INTERVAL_MINUTES`, `HEADLESS`, database settings.
- How to run it: `python3 app/scheduler.py`.
- How to test it: Start it once and confirm it runs an immediate scrape and then reschedules.
- Notes for future developers: The scheduler uses active platforms and active accounts from the database.

### Scrapers
- Description: Platform-specific scraping implementations.
- Main responsibilities: Login/session reuse, post extraction, deduplication support, and mapping into the shared post schema.
- Key technologies: Playwright, custom stealth helpers, SQLAlchemy models.
- Important files: `app/src/scrapers/base_scraper.py`, `app/src/scrapers/linkedin_company_scraper.py`, `app/src/scrapers/linkedin_scraper.py`, `app/src/scrapers/facebook_scraper.py`, `app/src/scrapers/instagram_scraper.py`, `app/src/scrapers/x_scraper.py`.
- How to run them: Through `app/api_server.py`, `app/main.py`, `app/scheduler.py`, or `app/cli.py`.
- Notes for future developers: Scrapers stop early when they encounter a post URL already stored in the database for that platform.

### Database Layer
- Description: Async persistence layer for platforms, accounts, monitored URLs, posts, media, and scraper logs.
- Main responsibilities: CRUD operations, deduplication checks, platform seeding, and monitored URL handling.
- Key technologies: SQLAlchemy async ORM, Alembic migrations.
- Important files: `app/src/database/models.py`, `app/src/database/db_manager.py`, `alembic/versions/*`.
- How to run it: Accessed automatically by the app after `db.init_db()` and migration setup.
- How to test it: Verify migrations with `alembic upgrade head` and inspect via CLI stats or direct queries.
- Notes for future developers: `platforms.name + monitored_urls.url` and `platform_id + posts.external_id` are the key uniqueness rules.

### Utility Layer
- Description: Shared browser stealth and credential encryption helpers.
- Main responsibilities: Browser context setup, human-like pacing, session save/load, and password encryption.
- Key technologies: Playwright, cryptography, Faker.
- Important files: `app/src/utils/stealth.py`, `app/src/utils/encryption.py`.
- Notes for future developers: Session files are stored under `USER_DATA_DIR` and are platform-specific.

## Tech Stack
- Python 3.8+
- FastAPI
- Playwright
- SQLAlchemy 2.x
- Alembic
- Pydantic v2 / Pydantic Settings
- OpenPyXL
- APScheduler
- Loguru
- Cryptography
- SQLite or PostgreSQL, depending on `DATABASE_URL`

## Repository Structure
```text
social-monitor/
├── app/
│   ├── api_server.py        # FastAPI app, REST API, WebSocket, Excel export
│   ├── main.py              # Main orchestrator
│   ├── scheduler.py         # Scheduled scraper runner
│   ├── cli.py               # CLI entry point
│   ├── capture_session.py    # Manual session capture helper
│   ├── company_scraper.py   # Legacy/compatibility scraper entry point
│   ├── config/settings.py    # Environment-driven settings
│   └── src/
│       ├── database/         # Models and async DB manager
│       ├── scrapers/         # LinkedIn, Facebook, Instagram, X scrapers
│       └── utils/            # Stealth and encryption helpers
├── web/                      # HTML, JS, CSS, and images for the dashboard
├── alembic/                  # Database migrations
├── requirements.txt          # Python dependencies
├── setup.sh                  # Bootstrap script for local setup
├── start.sh                  # Starts the API server with .venv loading
├── x-cookie.py               # Helper to export X session cookies
└── README.md                 # This documentation
```

## Prerequisites
- Python 3.8 or newer.
- A local or remote PostgreSQL/SQLite database reachable through `DATABASE_URL`.
- Playwright Chromium installed.
- A writable `browser_profiles/` directory for session files.
- A valid `ENCRYPTION_KEY` in `.env`.

## Installation
1. Clone or unpack the repository.
2. Create and activate the virtual environment.
3. Install dependencies.
4. Install Playwright Chromium.
5. Run Alembic migrations.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
alembic upgrade head
```

If you want the automated bootstrap path, use `./setup.sh`.

## Configuration
The app reads configuration from `.env` through `app/config/settings.py`.

| Name | Required | Purpose | Used in |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | Async SQLAlchemy database URL | `app/config/settings.py`, `app/src/database/db_manager.py` |
| `ENCRYPTION_KEY` | Yes | Fernet key for encrypting stored account passwords | `app/src/utils/encryption.py` |
| `HEADLESS` | Yes | Default browser mode for scrapers | `app/config/settings.py`, `app/api_server.py`, `app/cli.py` |
| `RUN_PARALLEL` | No | Run platform jobs concurrently in the API scraper flow | `app/config/settings.py`, `app/api_server.py` |
| `USER_DATA_DIR` | No | Directory for browser session JSON files | `app/config/settings.py`, `app/src/utils/stealth.py` |
| `USE_PROXY` | No | Enables proxy support in Playwright context creation | `app/config/settings.py`, `app/src/utils/stealth.py` |
| `PROXY_URL` | No | Proxy server URL | `app/config/settings.py`, `app/src/utils/stealth.py` |
| `LOG_LEVEL` | No | Loguru log level | `app/config/settings.py`, `app/main.py`, `app/api_server.py` |
| `LOG_FILE` | No | Log file path | `app/config/settings.py`, `app/main.py` |
| `MIN_DELAY` | No | Minimum scrape delay in seconds | `app/config/settings.py`, `app/src/utils/stealth.py` |
| `MAX_DELAY` | No | Maximum scrape delay in seconds | `app/config/settings.py`, `app/src/utils/stealth.py` |
| `PAGE_LOAD_TIMEOUT` | No | Page timeout in milliseconds | `app/config/settings.py` |
| `SCROLL_DELAY_MIN` | No | Minimum scroll delay | `app/config/settings.py` |
| `SCROLL_DELAY_MAX` | No | Maximum scroll delay | `app/config/settings.py` |
| `SCRAPE_INTERVAL_MINUTES` | No | Default scheduled scrape interval | `app/config/settings.py`, `app/scheduler.py` |
| `LINKEDIN_ENABLED` | No | Legacy LinkedIn toggle in settings | `app/config/settings.py`, `app/main.py` |
| `FACEBOOK_ENABLED` | No | Legacy Facebook toggle in settings | `app/config/settings.py`, `app/main.py` |
| `TWITTER_ENABLED` | No | Legacy X/Twitter toggle in settings | `app/config/settings.py`, `app/main.py` |

Notes:
- The web UI now controls platform activation through the `platforms` table, not through settings.
- `HEADLESS` and `RUN_PARALLEL` are global app settings.

## Running Locally
### API and Web UI
```bash
source .venv/bin/activate
./start.sh
```
This starts `uvicorn app.api_server:app --reload` and serves the dashboard.

### CLI
```bash
source .venv/bin/activate
python3 app/cli.py help
```

### Main Application
```bash
source .venv/bin/activate
python3 app/main.py
```

### Scheduler
```bash
source .venv/bin/activate
python3 app/scheduler.py
```

## Available Scripts and Commands
- `./setup.sh`: Creates `.venv`, installs dependencies, installs Chromium, creates `.env` if missing, and creates runtime directories.
- `./start.sh`: Loads `.env`, activates `.venv` if present, and starts the FastAPI app with Uvicorn.
- `python3 app/cli.py help`: Prints CLI usage.
- `python3 app/cli.py add-account ...`: Adds a database-backed account.
- `python3 app/cli.py list-accounts`: Lists stored accounts.
- `python3 app/cli.py list-posts [platform] [limit]`: Lists stored posts.
- `python3 app/cli.py stats`: Prints counts by platform, account, and post.
- `python3 app/cli.py scrape <platform> <username> <password> [--headless/--no-headless]`: Runs one scraper manually.
- `python3 app/main.py`: Starts the main orchestrator.
- `python3 app/scheduler.py`: Starts the scheduled monitor.
- `python3 app/capture_session.py --platform ...`: Manually captures a browser session file.
- `python3 x-cookie.py`: Exports X session cookies into `browser_profiles/x_session.json`.
- `alembic upgrade head`: Applies schema migrations.
- `alembic revision --autogenerate -m "message"`: Creates a new migration.

## API Documentation
Source file: `app/api_server.py`

### `GET /`
- Purpose: Serves the web dashboard.
- Response: `index.html`.

### `GET /api/platforms`
- Purpose: Lists all platforms.
- Response: `[{ id, name, is_active }]`.

### `PATCH /api/platforms/{platform_id}`
- Purpose: Enables or disables a platform.
- Body: `{ "is_active": true|false }`

### `GET /api/settings`
- Purpose: Returns global settings used by the UI.
- Response: `{ "headless": bool, "run_parallel": bool }`

### `PATCH /api/settings`
- Purpose: Updates global settings.
- Body: `{ "headless": bool, "run_parallel": bool }`

### `GET /api/accounts`
- Purpose: Lists all stored accounts.
- Response: Array of account records with platform ID, username, email, status, and timestamps.

### `POST /api/accounts`
- Purpose: Creates a new account.
- Body: `{ platform, username, email, password, is_active }`

### `PATCH /api/accounts/{account_id}`
- Purpose: Updates account active state.
- Body: `{ "is_active": bool }`

### `DELETE /api/accounts/{account_id}`
- Purpose: Deletes an account.

### `GET /api/monitored-urls`
- Purpose: Lists all monitored URLs.
- Response: Array with platform ID, URL, label, active flag, and timestamps.

### `POST /api/monitored-urls`
- Purpose: Creates one monitored URL.
- Body: `{ platform, url, label, is_active }`
- Validation: URL is normalized and duplicate URLs are rejected.

### `PATCH /api/monitored-urls/{monitored_id}`
- Purpose: Updates a monitored URL.
- Validation: URL is normalized and duplicates are rejected.

### `POST /api/monitored-urls/upload`
- Purpose: Bulk uploads monitored URLs from `.csv` or `.xlsx`.
- Required columns: `label`, `linkedin`, `facebook`, `instagram`, `x`.
- Behavior: Nonblank URLs become active monitored URLs, duplicates are skipped.

### `DELETE /api/monitored-urls/{monitored_id}`
- Purpose: Deletes a monitored URL.

### `POST /api/run-scrape`
- Purpose: Starts a scrape job in the background.
- Body: Optional `{ "platforms": ["linkedin", ...] }`.

### `GET /api/download-new`
- Purpose: Downloads new posts as an Excel workbook.
- Response: `Social Media Monitoring - YYYYMMDD.xlsx`.

### `WebSocket /ws`
- Purpose: Streams progress, status, milestone, error, and completion events to the dashboard.

## Data Models and Database
Source files: `app/src/database/models.py`, `app/src/database/db_manager.py`, `alembic/versions/*`

### `platforms`
- Fields: `id`, `name`, `base_url`, `is_active`, `last_scraped_at`, `created_at`
- Relationships: accounts, posts, monitored URLs
- Notes: platform activation is controlled here.

### `accounts`
- Fields: `platform_id`, `username`, `email`, `password_encrypted`, `is_active`, `session_valid`, `last_login_at`, `cookies_data`, `user_agent`
- Notes: passwords are encrypted before storage.

### `posts`
- Fields: `platform_id`, `external_id`, `post_url`, `author_name`, `author_username`, `author_url`, `content`, `posted_at`, `scraped_at`, engagement counts, flags, `raw_data`
- Notes: unique index on `platform_id + external_id`.

### `monitored_urls`
- Fields: `platform_id`, `url`, `label`, `is_active`, `last_checked_at`, `last_exported_at`, `created_at`, `updated_at`
- Notes: unique index on `platform_id + url`.

### `media`
- Fields: `post_id`, `media_type`, `media_url`, `thumbnail_url`, `width`, `height`, `duration`, `file_size`

### `scraper_logs`
- Fields: `platform_id`, `account_id`, `log_level`, `message`, `error_details`, `posts_scraped`, `new_posts_count`, timestamps

### Migrations
- `alembic/versions/20260211_150000_initial_schema.py`
- `alembic/versions/20260211_153000_add_last_exported_at.py`

## Authentication and Authorization
- The app does not implement end-user authentication or authorization.
- Platform logins are handled through browser sessions stored under `USER_DATA_DIR`.
- LinkedIn uses account selection/session reuse when available.
- X uses a single session file: `browser_profiles/x_session.json`.
- Facebook and Instagram also rely on session capture and reuse.
- Relevant files: `app/src/utils/stealth.py`, `app/capture_session.py`, `x-cookie.py`, the platform scrapers.

## Testing
- There is no automated test suite checked into the repository.
- Practical verification is currently done by:
  - Running `python3 app/cli.py stats`
  - Starting the API and checking the dashboard
  - Running a scrape from the UI or CLI
  - Confirming migrations with `alembic upgrade head`
- If tests are added later, document their location and invocation here.

## Build and Deployment
- Local development uses `setup.sh` and `start.sh`.
- `setup.sh` creates the virtual environment, installs dependencies, installs Chromium, creates runtime directories, and bootstraps `.env` if needed.
- `start.sh` loads `.env`, activates `.venv` if present, and starts Uvicorn with reload.
- `DEPLOYMENT.md` describes a VPS-oriented deployment approach using `systemd`, `supervisor`, or `screen`.
- `browser_profiles/`, `logs/`, and `data/` are runtime directories that must be writable by the process.

## Development Notes
- The web UI is the primary operational interface now.
- Platform activation is stored in the database and surfaced through `/api/platforms`.
- `HEADLESS` and `RUN_PARALLEL` are global settings stored in `.env`.
- Scrapers stop early when they encounter a post URL already stored for the same platform, which keeps runs incremental.
- Existing docs like `QUICKSTART.md` and `DEPLOYMENT.md` still contain older wording about templates and old toggles, so treat this README as the source of truth until those docs are updated.

## Troubleshooting
- If the browser does not start visibly, confirm `HEADLESS=false` in `.env` and restart the API server.
- If the app exits immediately, verify `DATABASE_URL` points to an accessible database and `alembic upgrade head` has been run.
- If a monitored URL fails with `ERR_ABORTED`, check that the URL is valid and starts with `http://` or `https://`.
- If uploads fail, confirm `python-multipart` is installed, since FastAPI needs it for file uploads.
- If sessions are not reused, verify the matching file exists under `browser_profiles/`.

## Maintenance Checklist
- Update the environment variable table when config changes.
- Update the API section when routes change.
- Update platform notes when a scraper behavior changes.
- Update migration notes when schema changes.
- Update startup commands when `setup.sh` or `start.sh` changes.
- Keep the troubleshooting section aligned with actual runtime failures.
