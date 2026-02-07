"""
Advanced stealth utilities for undetectable browser automation
"""

import asyncio
import random
from typing import Optional, Tuple

from faker import Faker
from playwright.async_api import BrowserContext, Page

fake = Faker()


class StealthConfig:
    """Configuration for stealth behavior"""

    # Realistic typing speeds (chars per second)
    TYPING_SPEED_MIN = 8
    TYPING_SPEED_MAX = 15

    # Mouse movement
    MOUSE_MOVE_STEPS = random.randint(10, 25)

    # Viewport sizes (common resolutions) - keep steady to avoid resizing between runs
    VIEWPORTS = [
        {"width": 1366, "height": 768},
    ]

    # User agents (latest Chrome versions)
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]


class HumanBehavior:
    """Simulate human-like interactions"""

    @staticmethod
    async def random_delay(min_seconds: float = 2.5, max_seconds: float = 7.0):
        """Random delay with human-like variance"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    @staticmethod
    async def micro_sleep():
        """Very short random sleep (0.1-0.3s)"""
        await asyncio.sleep(random.uniform(0.1, 0.3))

    @staticmethod
    async def human_type(
        page: Page, selector: str, text: str, delay_range: Tuple[int, int] = (50, 150)
    ):
        """Type text with human-like speed and mistakes"""
        element = await page.wait_for_selector(selector, timeout=10000)
        await element.click()
        await HumanBehavior.micro_sleep()

        for char in text:
            await element.type(char, delay=random.randint(*delay_range))

            # Occasionally pause (like thinking)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.5, 1.5))

    @staticmethod
    async def human_scroll(page: Page, scrolls: int = 3):
        """Scroll page naturally like a human"""
        viewport_height = page.viewport_size["height"]

        for _ in range(scrolls):
            # Random scroll distance (not full page)
            scroll_amount = random.randint(
                int(viewport_height * 0.3), int(viewport_height * 0.8)
            )

            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await HumanBehavior.random_delay(1.5, 4.0)

            # Sometimes scroll back up a bit (like re-reading)
            if random.random() < 0.2:
                back_scroll = random.randint(100, 300)
                await page.evaluate(f"window.scrollBy(0, -{back_scroll})")
                await HumanBehavior.micro_sleep()

    @staticmethod
    async def random_mouse_movement(page: Page):
        """Move mouse randomly across the page"""
        viewport = page.viewport_size

        for _ in range(random.randint(2, 5)):
            x = random.randint(100, viewport["width"] - 100)
            y = random.randint(100, viewport["height"] - 100)

            await page.mouse.move(x, y)
            await HumanBehavior.micro_sleep()

    @staticmethod
    async def occasional_pause(probability: float = 0.15):
        """Random pause to simulate user thinking/distraction"""
        if random.random() < probability:
            await asyncio.sleep(random.uniform(3.0, 8.0))


class StealthBrowser:
    """Enhanced browser context with stealth features"""

    @staticmethod
    async def create_stealth_context(
        browser, proxy: Optional[str] = None
    ) -> BrowserContext:
        """Create a browser context with maximum stealth"""

        viewport = random.choice(StealthConfig.VIEWPORTS)
        user_agent = random.choice(StealthConfig.USER_AGENTS)

        context_options = {
            "viewport": viewport,
            "user_agent": user_agent,
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "permissions": ["geolocation", "notifications"],
            "geolocation": {"latitude": 40.7128, "longitude": -74.0060},  # New York
            "color_scheme": "light",
            "device_scale_factor": 1,
            "has_touch": False,
            "is_mobile": False,
        }

        if proxy:
            context_options["proxy"] = {"server": proxy}

        context = await browser.new_context(**context_options)

        # Add stealth scripts
        await StealthBrowser._inject_stealth_scripts(context)

        return context

    @staticmethod
    async def _inject_stealth_scripts(context: BrowserContext):
        """Inject JavaScript to pass bot detection"""

        # Remove webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Fake plugins
        await context.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    }
                ]
            });
        """)

        # Fake languages
        await context.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

        # Override permissions
        await context.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        # Chrome runtime
        await context.add_init_script("""
            window.chrome = {
                runtime: {}
            };
        """)

        # Canvas fingerprint randomization
        await context.add_init_script("""
            const getImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(...args) {
                const imageData = getImageData.apply(this, args);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] = imageData.data[i] + Math.floor(Math.random() * 3) - 1;
                }
                return imageData;
            };
        """)


class SessionManager:
    """Manage browser sessions and cookies"""

    @staticmethod
    async def save_session(context: BrowserContext, platform: str, account_id: int):
        """Save cookies and session storage"""
        cookies = await context.cookies()
        storage = await context.storage_state()

        # Save to file
        import json

        session_file = f"./browser_profiles/{platform}_{account_id}_session.json"
        with open(session_file, "w") as f:
            json.dump(storage, f)

    @staticmethod
    async def load_session(
        context: BrowserContext, platform: str, account_id: int
    ) -> bool:
        """Load saved session"""
        import json
        import os

        session_file = f"./browser_profiles/{platform}_{account_id}_session.json"
        if not os.path.exists(session_file):
            return False

        try:
            with open(session_file, "r") as f:
                storage_state = json.load(f)

            # Apply cookies
            await context.add_cookies(storage_state.get("cookies", []))
            return True
        except Exception:
            return False


# Export key classes
__all__ = ["HumanBehavior", "StealthBrowser", "SessionManager", "StealthConfig"]
