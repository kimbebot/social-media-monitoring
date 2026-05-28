"""
Facebook profile/page scraper.
Best-effort extraction; relies on session reuse to avoid login prompts.
"""
from datetime import datetime
import hashlib
from typing import Dict, List, Optional

from loguru import logger

from app.src.utils.stealth import HumanBehavior
from .base_scraper import BaseScraper


class FacebookScraper(BaseScraper):
    """Scrape posts from Facebook profiles/pages."""

    def __init__(self):
        super().__init__("facebook")

    def get_base_url(self) -> str:
        return "https://www.facebook.com"

    async def perform_login(self, username: str, password: str) -> bool:
        """Best-effort login; prefers session reuse."""
        try:
            await self.page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
            await HumanBehavior.random_delay(2, 3)

            try:
                await HumanBehavior.human_type(self.page, 'input[name="email"]', username)
                await HumanBehavior.human_type(self.page, 'input[name="pass"]', password)
                await HumanBehavior.random_delay(1, 2)
                await self.page.locator('button[name="login"]').first.click()
            except Exception as e:
                logger.warning(f"Could not fill credentials: {e}")

            try:
                await self.page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass

            return await self.verify_session()
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def verify_session(self) -> bool:
        """Verify Facebook session."""
        try:
            await self.page.goto("https://www.facebook.com/", timeout=15000)
            await HumanBehavior.random_delay(2, 3)
            current_url = self.page.url.lower()
            if "login" in current_url or "checkpoint" in current_url:
                return False
            login_form = await self.page.query_selector('input[name="email"], input[name="pass"]')
            if login_form:
                return False
            return True
        except Exception:
            return False

    async def scrape_feed(self) -> List[Dict]:
        return []

    async def scrape_profile_posts(self, profile_url: str, limit: int = 5) -> List[Dict]:
        logger.info(f"Scraping Facebook posts from: {profile_url}")
        posts: List[Dict] = []

        try:
            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(2, 3)

            target_limit = None if limit <= 0 else limit
            posts = await self._scrape_posts_from_feed(profile_url, target_limit)

            logger.success(f"✓ Scraped {len(posts)} posts from Facebook profile/page")
        except Exception as e:
            logger.error(f"Error scraping Facebook profile/page: {e}")

        return posts

    async def _collect_post_links(self, target_limit: Optional[int]) -> List[str]:
        max_scrolls = 30
        stable_rounds = 0
        seen: List[str] = []
        seen_set = set()

        for _ in range(max_scrolls):
            links = await self.page.query_selector_all(
                'a[href*="/posts/"], a[href*="permalink.php"], a[href*="story_fbid="], a[href*="fbid="], a[href*="/photo/"], a[href*="/photos/"]'
            )
            new_found = 0
            for link in links:
                href = await link.get_attribute("href")
                if not href:
                    continue
                post_url = self._normalize_url(href)
                if not post_url:
                    continue
                if post_url in seen_set:
                    continue
                seen_set.add(post_url)
                seen.append(post_url)
                new_found += 1

            if target_limit and len(seen) >= target_limit:
                break

            if new_found == 0:
                stable_rounds += 1
            else:
                stable_rounds = 0

            if stable_rounds >= 4:
                break

            await HumanBehavior.human_scroll(self.page, scrolls=2)
            await HumanBehavior.random_delay(2, 4)

        if target_limit and len(seen) < target_limit:
            logger.warning(f"Only found {len(seen)} post links (target={target_limit})")

        return seen

    async def _scrape_post_detail(self, post_url: str) -> Dict:
        data: Dict = {"content": "", "posted_at": None, "likes_count": 0, "comments_count": 0, "media": []}
        try:
            await self.page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(1.5, 2.5)

            # Content
            content = await self.page.evaluate(
                """
                () => {
                  const extract = (el) => (el ? el.innerText.trim() : "");
                  const selectors = [
                    'div[data-ad-preview="message"]',
                    'div[role="article"] div[dir="auto"]',
                  ];
                  let longest = "";
                  for (const sel of selectors) {
                    const nodes = Array.from(document.querySelectorAll(sel));
                    for (const node of nodes) {
                      const text = extract(node);
                      if (text && text.length > longest.length) {
                        longest = text;
                      }
                    }
                  }
                  return longest;
                }
                """
            )
            if content:
                data["content"] = content

            # Author
            author_el = await self.page.query_selector('strong a[role="link"], h2 a[role="link"]')
            if author_el:
                data["author_name"] = await author_el.inner_text()

            # Posted time
            time_el = await self.page.query_selector("abbr, span[data-testid='story-subtitle'] time, time")
            if time_el:
                dt = await time_el.get_attribute("datetime")
                if dt:
                    data["posted_at"] = dt

            return data
        except Exception as e:
            logger.warning(f"Facebook post detail failed: {e}")
            return data

    def _extract_post_id(self, post_url: str) -> str:
        for token in ("story_fbid=", "fbid=", "/posts/"):
            if token in post_url:
                return post_url.split(token, 1)[-1].split("/", 1)[0]
        return post_url.rstrip("/").split("/")[-1]

    def _normalize_url(self, href: str) -> Optional[str]:
        if not href:
            return None
        href = href.strip()
        if href.startswith("http://") or href.startswith("https://"):
            return href.split("?")[0]
        if href.startswith("/"):
            return f"https://www.facebook.com{href}".split("?")[0]
        return None

    async def save_company_posts(self, posts: List[Dict]) -> int:
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
    async def _scrape_posts_from_feed(
        self, profile_url: str, target_limit: Optional[int]
    ) -> List[Dict]:
        max_scrolls = 1
        seen_post_ids = set()
        collected: List[Dict] = []

        post_container_selector = "div.x1yztbdb.x1n2onr6.xh8yej3.x1ja2u2z"

        # Conservative pacing to reduce risk
        await HumanBehavior.random_delay(4, 7)

        # Pre-scroll to load more items before extraction
        await HumanBehavior.human_scroll(self.page, scrolls=4)
        await HumanBehavior.random_delay(5, 9)

        for _ in range(max_scrolls):
            posts = self.page.locator(post_container_selector)
            count = await posts.count()

            for idx in range(count):
                if target_limit and len(collected) >= target_limit:
                    break
                post_container = posts.nth(idx)
                post_url = await self._extract_post_url_from_container(post_container)
                if post_url and await self.post_url_exists(post_url):
                    logger.info(
                        f"Encountered existing Facebook post URL; stopping scan for {profile_url}"
                    )
                    return collected
                post = await self._extract_post_from_container(post_container, profile_url)
                if not post:
                    continue
                post_id = post.get("post_id")
                if not post_id or post_id in seen_post_ids:
                    continue
                seen_post_ids.add(post_id)
                collected.append(post)
                await HumanBehavior.random_delay(2.5, 4.5)
                if len(collected) % 3 == 0:
                    await HumanBehavior.random_delay(5, 8)

            if target_limit and len(collected) >= target_limit:
                break

            break

        if target_limit and len(collected) < target_limit:
            logger.warning(f"Only found {len(collected)} posts (target={target_limit})")

        return collected

    async def _extract_post_url_from_container(self, container) -> Optional[str]:
        try:
            post_url = await container.evaluate(
                """
                (el) => {
                  const selectors = [
                    'a[href*="/posts/"]',
                    'a[href*="permalink.php"]',
                    'a[href*="story_fbid="]',
                    'a[href*="fbid="]',
                    'a[href*="/photo/"]',
                    'a[href*="/photos/"]',
                  ];
                  for (const sel of selectors) {
                    const link = el.querySelector(sel);
                    if (link && link.getAttribute("href")) {
                      return link.getAttribute("href");
                    }
                  }
                  return "";
                }
                """
            )
        except Exception:
            return None
        return self._normalize_url(post_url) if post_url else None

    async def _extract_post_from_container(self, container, profile_url: str) -> Optional[Dict]:
        try:
            # Expand "See more" inside the post container if present
            try:
                more = container.locator(
                    'div[role="button"]:has-text("See more"), span:has-text("See more"), a:has-text("See more")'
                )
                if await more.count() > 0:
                    for idx in range(min(2, await more.count())):
                        await more.nth(idx).click()
                        await HumanBehavior.random_delay(0.4, 0.8)
            except Exception:
                pass

            content = await container.evaluate(
                """
                (el) => {
                  const contentWrapper = el.querySelector(
                    "div.x1n2onr6.x1ja2u2z.x1jx94hy.xw5cjc7.x1dmpuos.x1vsv7so.xau1kf4.x9f619.xh8yej3.x6ikm8r.x10wlt62.xquyuld"
                  );
                  if (!contentWrapper) return "";
                  const htmlDivs = contentWrapper.querySelectorAll("div.html-div");
                  const target = htmlDivs[9];
                  if (!target) return "";
                  const firstInnerDiv = target.querySelector("div");
                  return firstInnerDiv ? firstInnerDiv.innerText.trim() : "";
                }
                """
            )

            post_url = await self._extract_post_url_from_container(container)

            author_name = await container.evaluate(
                """
                (el) => {
                  const link = el.querySelector('strong a[role="link"], h2 a[role="link"]');
                  return link ? link.textContent.trim() : "";
                }
                """
            )

            posted_at = await container.evaluate(
                """
                (el) => {
                  const time = el.querySelector("abbr, time");
                  return time ? (time.getAttribute("datetime") || "") : "";
                }
                """
            )

            post_id = None
            if post_url:
                post_id = self._extract_post_id(post_url)
            else:
                signature = f"{author_name}|{posted_at}|{content}"
                post_id = hashlib.sha1(signature.encode("utf-8")).hexdigest()

            return {
                "post_id": post_id,
                "company_name": author_name or None,
                "company_url": profile_url,
                "post_url": post_url or profile_url,
                "content": content or "",
                "posted_at": posted_at or datetime.utcnow().isoformat(),
                "posted_at_text": None,
                "likes_count": 0,
                "comments_count": 0,
                "shares_count": 0,
                "media": [],
                "scraped_at": datetime.utcnow().isoformat(),
            }
        except Exception:
            return None
