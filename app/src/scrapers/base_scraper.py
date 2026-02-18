"""
Base scraper class with stealth capabilities
All platform-specific scrapers inherit from this
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from app.config.settings import settings
from app.src.database.db_manager import db
from app.src.database.models import Account, Platform
from app.src.utils.encryption import encryption
from app.src.utils.stealth import HumanBehavior, SessionManager, StealthBrowser


class BaseScraper(ABC):
    """Base class for all social media scrapers"""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.platform: Optional[Platform] = None
        self.account: Optional[Account] = None
        self.scraper_log_id: Optional[int] = None

    async def initialize(self):
        """Initialize scraper and database"""
        logger.info(f"Initializing {self.platform_name} scraper")

        # Get or create platform
        self.platform = await db.get_or_create_platform(
            name=self.platform_name, base_url=self.get_base_url()
        )

        # Create scraper log
        log_data = {
            "platform_id": self.platform.id,
            "log_level": "INFO",
            "message": f"Starting {self.platform_name} scraper",
            "started_at": datetime.utcnow(),
        }
        log = await db.create_scraper_log(log_data)
        self.scraper_log_id = log.id

    async def start_browser(self, headless: bool = None):
        """Start browser with stealth configuration"""
        if headless is None:
            headless = settings.headless

        logger.info(f"Starting browser (headless={headless})")
        logger.info(f"Settings headless={settings.headless}")

        playwright = await async_playwright().start()

        # Launch browser with specific args to avoid detection
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
            ],
        )

        # Create stealth context
        self.context = await StealthBrowser.create_stealth_context(
            self.browser, proxy=settings.proxy_url if settings.use_proxy else None
        )

        # Create page
        self.page = await self.context.new_page()

        # Set extra headers
        await self.page.set_extra_http_headers(
            {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

    async def login(self, username: str, password: str) -> bool:
        """
        Login to the platform
        Should be implemented by each platform-specific scraper
        """
        logger.info(f"Attempting login for user: {username}")

        # Get account from database
        self.account = await db.get_account(self.platform.id, username)

        if not self.account:
            logger.error(f"Account {username} not found in database")
            return False

        # Decrypt password
        decrypted_password = encryption.decrypt(self.account.password_encrypted)

        # Try to load existing session
        session_loaded = await SessionManager.load_session(
            self.context,
            self.platform_name,
            self.account.username,
        )

        if session_loaded:
            logger.info("Loaded existing session")
            # Verify session is still valid
            if await self.verify_session():
                # Some platforms prompt for account selection after session restore
                if await self._maybe_handle_account_selection():
                    logger.info("Account selection handled after session restore")
                logger.success("Session is valid, skipping login")
                return True
            else:
                logger.warning("Session invalid after load; will perform fresh login")

        # Perform actual login
        logger.info("Performing fresh login")
        success = await self.perform_login(username, decrypted_password)

        if success:
            # Save session
            await SessionManager.save_session(
                self.context,
                self.platform_name,
                self.account.username,
            )

            # Update database
            cookies = await self.context.cookies()
            user_agent = await self.page.evaluate("navigator.userAgent")
            await db.update_account_session(
                self.account.id, {"cookies": cookies}, user_agent
            )

            logger.success("Login successful")
        else:
            logger.error("Login failed")

        return success

    async def _maybe_handle_account_selection(self) -> bool:
        """
        Hook for platform-specific account selection after session restore.
        Default no-op; override in platform scrapers as needed.
        """
        return False

    @abstractmethod
    async def perform_login(self, username: str, password: str) -> bool:
        """Platform-specific login implementation"""
        pass

    @abstractmethod
    async def verify_session(self) -> bool:
        """Verify if current session is valid"""
        pass

    @abstractmethod
    async def scrape_feed(self) -> List[Dict]:
        """Scrape posts from user's feed"""
        pass

    @abstractmethod
    def get_base_url(self) -> str:
        """Return platform's base URL"""
        pass

    async def save_posts(self, posts: List[Dict]) -> int:
        """Save scraped posts to database"""
        if not posts:
            logger.warning("No posts to save")
            return 0

        logger.info(f"Saving {len(posts)} posts to database")

        # Add platform_id to each post
        for post in posts:
            post["platform_id"] = self.platform.id

        # Bulk create posts
        new_count = await db.bulk_create_posts(posts)
        logger.success(
            f"Saved {new_count} new posts (skipped {len(posts) - new_count} duplicates)"
        )

        return new_count

    async def run(self, username: str, password: str) -> Dict:
        """Main execution flow"""
        start_time = datetime.utcnow()
        stats = {"success": False, "posts_scraped": 0, "new_posts": 0, "error": None}

        try:
            await self.initialize()
            await self.start_browser()

            # Login
            if not await self.login(username, password):
                raise Exception("Login failed")

            # Human-like pause after login
            await HumanBehavior.random_delay(3, 6)

            # Scrape feed
            posts = await self.scrape_feed()
            stats["posts_scraped"] = len(posts)

            # Save posts
            stats["new_posts"] = await self.save_posts(posts)
            stats["success"] = True

        except Exception as e:
            logger.error(f"Scraper error: {str(e)}")
            stats["error"] = str(e)

            # Update log with error
            if self.scraper_log_id:
                await db.update_scraper_log(
                    self.scraper_log_id, {"log_level": "ERROR", "error_details": str(e)}
                )

        finally:
            # Cleanup
            await self.cleanup()

            # Update log
            if self.scraper_log_id:
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                await db.update_scraper_log(
                    self.scraper_log_id,
                    {
                        "completed_at": end_time,
                        "duration_seconds": int(duration),
                        "posts_scraped": stats["posts_scraped"],
                        "new_posts_count": stats["new_posts"],
                    },
                )

        return stats

    async def cleanup(self):
        """Close browser and cleanup resources"""
        logger.info("Cleaning up resources")

        if self.page:
            await self.page.close()

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()
