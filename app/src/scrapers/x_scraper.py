"""
X (Twitter) profile scraper
Scrapes posts from profile URLs using existing sessions when possible.
"""
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from app.src.utils.stealth import HumanBehavior
from .base_scraper import BaseScraper


class XScraper(BaseScraper):
    """Scrape posts from X profile pages"""

    def __init__(self, platform_name: str = "x"):
        super().__init__(platform_name)

    def get_base_url(self) -> str:
        return "https://x.com"

    async def perform_login(self, username: str, password: str) -> bool:
        """Session-only for X; do not attempt login."""
        logger.warning("X login disabled (session-only mode).")
        return False

    async def verify_session(self) -> bool:
        """Verify X session is valid."""
        try:
            await self.page.goto("https://x.com/home", timeout=15000)
            await HumanBehavior.random_delay(2, 3)
            current_url = self.page.url.lower()
            if "login" in current_url or "i/flow" in current_url:
                return False
            return True
        except Exception:
            return False

    async def scrape_feed(self) -> List[Dict]:
        """Not used for profile scraping."""
        return []

    async def scrape_profile_posts(self, profile_url: str, limit: int = 10) -> List[Dict]:
        """Scrape posts from an X profile URL."""
        logger.info(f"Scraping X profile posts from: {profile_url}")
        posts: List[Dict] = []

        try:
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(2, 3)

            target_limit = None if limit <= 0 else limit
            max_scrolls = 30
            stable_rounds = 0
            last_count = 0

            for _ in range(max_scrolls):
                articles = await self.page.query_selector_all("article")
                current_count = len(articles)
                if current_count > last_count:
                    last_count = current_count
                    stable_rounds = 0
                else:
                    stable_rounds += 1

                if target_limit and current_count >= target_limit:
                    break
                if stable_rounds >= 3:
                    break

                await HumanBehavior.human_scroll(self.page, scrolls=2)
                await HumanBehavior.random_delay(2, 4)

            articles = await self.page.query_selector_all("article")
            seen_ids = set()

            for article in articles:
                if target_limit and len(posts) >= target_limit:
                    break
                post_data = await self._extract_post_data(article, profile_url)
                if not post_data:
                    continue
                if post_data["post_id"] in seen_ids:
                    continue
                seen_ids.add(post_data["post_id"])
                posts.append(post_data)

            logger.success(f"✓ Scraped {len(posts)} posts from X profile")
        except Exception as e:
            logger.error(f"Error scraping X profile: {e}")

        return posts

    async def save_company_posts(self, posts: List[Dict]) -> int:
        """Map X posts to DB schema and save."""
        if not posts:
            logger.warning("No posts to save")
            return 0

        mapped = []
        for post in posts:
            mapped_post = self._map_post_to_db(post)
            if mapped_post:
                mapped.append(mapped_post)

        if not mapped:
            logger.warning("No mappable posts to save")
            return 0

        return await self.save_posts(mapped)

    def _map_post_to_db(self, post: Dict) -> Optional[Dict]:
        """Map scraper post dict into Post model fields."""
        try:
            external_id = post.get("post_id")
            post_url = post.get("post_url")
            if not external_id or not post_url:
                return None

            posted_at = None
            posted_at_raw = post.get("posted_at")
            if posted_at_raw:
                try:
                    posted_at = datetime.fromisoformat(posted_at_raw)
                except Exception:
                    posted_at = None

            return {
                "external_id": external_id,
                "post_url": post_url,
                "author_name": post.get("company_name"),
                "author_url": post.get("company_url"),
                "content": post.get("content"),
                "posted_at": posted_at,
                "likes_count": post.get("likes_count", 0),
                "comments_count": post.get("comments_count", 0),
                "shares_count": post.get("shares_count", 0),
                "raw_data": post,
            }
        except Exception:
            return None

    async def _extract_post_data(self, article, profile_url: str) -> Optional[Dict]:
        """Extract data from a single post article."""
        try:
            link = await article.query_selector('a[href*="/status/"]')
            if not link:
                return None
            href = await link.get_attribute("href")
            if not href:
                return None

            post_url = href if href.startswith("http") else f"https://x.com{href}"
            post_id = href.split("/status/")[-1].split("?")[0]

            content = ""
            content_el = await article.query_selector('div[data-testid="tweetText"]')
            if content_el:
                content = await content_el.inner_text()

            posted_at = None
            time_el = await article.query_selector("time")
            if time_el:
                dt = await time_el.get_attribute("datetime")
                if dt:
                    try:
                        posted_at = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                    except Exception:
                        posted_at = None

            author_name = None
            author_el = await article.query_selector('div[data-testid="User-Name"]')
            if author_el:
                author_name = await author_el.inner_text()

            return {
                "post_id": post_id,
                "company_name": author_name,
                "company_url": profile_url,
                "post_url": post_url,
                "content": content.strip(),
                "posted_at": posted_at.isoformat() if posted_at else None,
                "posted_at_text": None,
                "likes_count": 0,
                "comments_count": 0,
                "shares_count": 0,
                "media": [],
                "scraped_at": datetime.utcnow().isoformat(),
            }
        except Exception:
            return None
