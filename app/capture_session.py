#!/usr/bin/env python3
"""
One-time session capture for social platforms.
Opens a visible browser, waits for manual login, saves storage_state to browser_profiles.
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config.settings import settings


def safe_key(value: str) -> str:
    if not value:
        return "unknown"
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip().lower())


async def main():
    parser = argparse.ArgumentParser(description="Capture session for a platform")
    parser.add_argument(
        "--platform",
        required=True,
        choices=["x", "instagram", "linkedin", "facebook"],
        help="Platform to capture session for",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="Username/email used to name the session file (not required for X)",
    )
    args = parser.parse_args()

    platform = args.platform
    session_dir = Path(settings.user_data_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    if platform == "x":
        session_file = session_dir / "x_session.json"
    else:
        username = (
            args.username or input("Enter username/email for session file: ").strip()
        )
        session_file = session_dir / f"{platform}_{safe_key(username)}_session.json"

    login_url = {
        "x": "https://x.com/login",
        "instagram": "https://www.instagram.com/accounts/login/",
        "linkedin": "https://www.linkedin.com/login",
        "facebook": "https://www.facebook.com/login",
    }[platform]

    print(f"Starting visible browser. Please log in to {platform} manually.")
    print("When you're fully logged in, press ENTER here to save session.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(login_url, wait_until="domcontentloaded")

        input("Press ENTER after you are fully logged in ...")

        storage = await context.storage_state()
        import json

        session_file.write_text(json.dumps(storage, indent=2))
        await context.close()
        await browser.close()

    print(f"Saved session to {session_file}")


if __name__ == "__main__":
    asyncio.run(main())
