# Quick Start Guide

This repository now uses [README.md](./README.md) as the source of truth for setup, configuration, API routes, and deployment notes.

## Fastest path

```bash
./setup.sh
source .venv/bin/activate
alembic upgrade head
./start.sh
```

## Common follow-up commands

```bash
python3 app/cli.py help
python3 app/cli.py stats
python3 app/main.py
python3 app/scheduler.py
```

## First run notes

- Add accounts through the web UI or `app/cli.py`.
- For LinkedIn, use a visible browser the first time if you need to complete login challenges.
- Session files are stored under `browser_profiles/`.

For the full documentation, use [README.md](./README.md).
