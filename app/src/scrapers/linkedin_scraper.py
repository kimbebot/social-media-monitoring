"""
LinkedIn Scraper
Scrapes posts from LinkedIn feed
"""

from datetime import datetime
from typing import Dict, List

from loguru import logger

from app.src.utils.stealth import HumanBehavior

from .base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):
    """LinkedIn-specific scraper implementation"""

    def __init__(self):
        super().__init__("linkedin")
        self.feed_url = "https://www.linkedin.com/feed/"

    def get_base_url(self) -> str:
        return "https://www.linkedin.com"

    async def perform_login(self, username: str, password: str) -> bool:
        """Login to LinkedIn"""
        try:
            # Navigate to LinkedIn
            await self.page.goto(
                "https://www.linkedin.com/login", wait_until="networkidle"
            )
            await HumanBehavior.random_delay(2, 4)

            # Type username with human-like behavior
            await HumanBehavior.human_type(self.page, "input#username", username)
            await HumanBehavior.micro_sleep()

            # Type password
            await HumanBehavior.human_type(self.page, "input#password", password)
            await HumanBehavior.random_delay(1, 2)

            # Click login button
            await self.page.click('button[type="submit"]')

            # Wait a moment to see what happens
            await HumanBehavior.random_delay(2, 4)

            # Check if CAPTCHA appeared on same page
            current_url = self.page.url
            if "login" in current_url and (
                "checkpoint" in current_url
                or "challenge" in current_url
                or await self._captcha_present()
            ):
                logger.warning("CAPTCHA/security check detected on login page")
                logger.info("⏳ Please solve the CAPTCHA in the browser window")
                logger.info("⏳ Waiting up to 5 minutes for you to complete it...")

                # Wait for user to solve CAPTCHA and submit
                for i in range(30):  # 5 minutes max
                    await HumanBehavior.random_delay(8, 12)
                    current_url = self.page.url

                    if "feed" in current_url or "mynetwork" in current_url:
                        logger.success("✅ Login successful after CAPTCHA!")
                        return True

                    if i % 3 == 0:
                        logger.info(
                            f"⏳ Still waiting... ({(i + 1) * 10} seconds elapsed)"
                        )

            # Wait for navigation
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            await HumanBehavior.random_delay(3, 5)

            # Check if login was successful
            current_url = self.page.url

            if "feed" in current_url or "mynetwork" in current_url:
                logger.success("LinkedIn login successful")
                return True
            elif "checkpoint" in current_url or "challenge" in current_url:
                logger.warning(
                    "LinkedIn security checkpoint detected - waiting for manual intervention..."
                )
                logger.info("Please complete CAPTCHA/2FA in the browser window")
                logger.info("Waiting up to 5 minutes...")

                # Wait longer for manual intervention (5 minutes max)
                # Check every 10 seconds if user completed it
                for i in range(30):  # 30 * 10 seconds = 5 minutes
                    await HumanBehavior.random_delay(8, 12)
                    current_url = self.page.url

                    if "feed" in current_url or "mynetwork" in current_url:
                        logger.success("Security checkpoint completed! Proceeding...")
                        return True

                    if i % 3 == 0:  # Every ~30 seconds
                        logger.info(
                            f"Still waiting... ({(i + 1) * 10} seconds elapsed)"
                        )

                # Final check
                return "feed" in self.page.url
            else:
                logger.error(f"Login failed, redirected to: {current_url}")
                return False

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False

    async def verify_session(self) -> bool:
        """Verify LinkedIn session is valid"""
        try:
            await self.page.goto(self.feed_url, timeout=15000)
            await HumanBehavior.random_delay(2, 3)

            # Check if we're on the feed page
            current_url = self.page.url
            if "feed" in current_url:
                logger.info("Session is valid")
                return True

            return False
        except Exception:
            return False

    async def _captcha_present(self) -> bool:
        """Check if CAPTCHA is present on page"""
        try:
            # Check for common CAPTCHA elements
            captcha_selectors = [
                'iframe[src*="recaptcha"]',
                'div[class*="captcha"]',
                'div[id*="captcha"]',
                "#captcha",
                ".g-recaptcha",
            ]

            for selector in captcha_selectors:
                element = await self.page.query_selector(selector)
                if element:
                    return True

            return False
        except Exception:
            return False

    async def scrape_feed(self) -> List[Dict]:
        """Scrape LinkedIn feed posts"""
        logger.info("Starting LinkedIn feed scrape")
        posts = []

        try:
            # Navigate to feed
            await self.page.goto(self.feed_url, wait_until="networkidle")
            await HumanBehavior.random_delay(3, 5)

            # Scroll to load more posts
            logger.info("Scrolling feed to load posts")
            await HumanBehavior.human_scroll(self.page, scrolls=5)

            # Wait for posts to load
            await self.page.wait_for_selector(
                "div.feed-shared-update-v2", timeout=10000
            )
            await HumanBehavior.random_delay(2, 4)

            # Get all post elements
            post_elements = await self.page.query_selector_all(
                "div.feed-shared-update-v2"
            )
            logger.info(f"Found {len(post_elements)} post elements")

            for idx, post_element in enumerate(post_elements[:20]):  # Limit to 20 posts
                try:
                    post_data = await self._extract_post_data(post_element)
                    if post_data:
                        if await self.post_url_exists(post_data.get("post_url")):
                            logger.info("Encountered existing LinkedIn feed post URL; stopping scan")
                            break
                        posts.append(post_data)
                        logger.debug(f"Extracted post {idx + 1}/{len(post_elements)}")

                    # Random micro-pause between posts
                    if idx % 5 == 0:
                        await HumanBehavior.micro_sleep()

                except Exception as e:
                    logger.warning(f"Error extracting post {idx}: {str(e)}")
                    continue

            logger.success(f"Successfully scraped {len(posts)} posts from LinkedIn")

        except Exception as e:
            logger.error(f"Error scraping feed: {str(e)}")

        return posts

    async def _extract_post_data(self, post_element) -> Dict:
        """Extract data from a single post element"""
        try:
            # Get post ID from data attribute or href
            post_id = await post_element.get_attribute("data-urn")
            if not post_id:
                # Try to extract from link
                link_element = await post_element.query_selector(
                    'a[href*="feed/update"]'
                )
                if link_element:
                    href = await link_element.get_attribute("href")
                    post_id = href.split("/")[-1] if href else None

            if not post_id:
                return None

            # Author information
            author_element = await post_element.query_selector(
                "span.update-components-actor__name"
            )
            author_name = (
                await author_element.inner_text() if author_element else "Unknown"
            )

            author_link = await post_element.query_selector(
                'a.app-aware-link[href*="/in/"]'
            )
            author_url = (
                await author_link.get_attribute("href") if author_link else None
            )

            # Extract username from URL
            author_username = None
            if author_url:
                author_username = author_url.split("/in/")[-1].split("?")[0]

            # Post content
            content_element = await post_element.query_selector(
                "div.feed-shared-update-v2__description"
            )
            content = await content_element.inner_text() if content_element else ""

            # Post URL
            post_url_element = await post_element.query_selector(
                'a[href*="feed/update"]'
            )
            post_url = (
                await post_url_element.get_attribute("href")
                if post_url_element
                else f"https://www.linkedin.com/feed/update/{post_id}"
            )

            # Engagement metrics
            likes_element = await post_element.query_selector(
                "span.social-details-social-counts__reactions-count"
            )
            likes_text = await likes_element.inner_text() if likes_element else "0"
            likes_count = self._parse_engagement_count(likes_text)

            comments_element = await post_element.query_selector(
                'button[aria-label*="comment"]'
            )
            comments_text = (
                await comments_element.inner_text() if comments_element else "0"
            )
            comments_count = self._parse_engagement_count(comments_text)

            # Timestamp
            time_element = await post_element.query_selector(
                "span.update-components-actor__sub-description"
            )
            posted_at_text = await time_element.inner_text() if time_element else None

            # Parse posted_at (LinkedIn uses relative times like "2h", "1d")
            posted_at = self._parse_linkedin_time(posted_at_text)

            return {
                "external_id": post_id,
                "post_url": post_url,
                "author_name": author_name.strip(),
                "author_username": author_username,
                "author_url": author_url,
                "content": content.strip(),
                "posted_at": posted_at,
                "likes_count": likes_count,
                "comments_count": comments_count,
                "shares_count": 0,  # LinkedIn doesn't show share count easily
                "scraped_at": datetime.utcnow(),
            }

        except Exception as e:
            logger.debug(f"Error in _extract_post_data: {str(e)}")
            return None

    def _parse_engagement_count(self, text: str) -> int:
        """Parse engagement count from text like '1,234' or '1K'"""
        try:
            text = text.strip().replace(",", "")
            if "K" in text:
                return int(float(text.replace("K", "")) * 1000)
            elif "M" in text:
                return int(float(text.replace("M", "")) * 1000000)
            else:
                # Extract just the number
                import re

                match = re.search(r"\d+", text)
                return int(match.group()) if match else 0
        except Exception:
            return 0

    def _parse_linkedin_time(self, time_text: str) -> datetime:
        """Parse LinkedIn relative time to datetime"""
        from datetime import timedelta

        if not time_text:
            return datetime.utcnow()

        time_text = time_text.lower().strip()
        now = datetime.utcnow()

        try:
            if "just now" in time_text or "now" in time_text:
                return now
            elif "minute" in time_text or "m" in time_text:
                minutes = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(minutes=minutes)
            elif "hour" in time_text or "h" in time_text:
                hours = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(hours=hours)
            elif "day" in time_text or "d" in time_text:
                days = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(days=days)
            elif "week" in time_text or "w" in time_text:
                weeks = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(weeks=weeks)
            elif "month" in time_text or "mo" in time_text:
                months = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(days=months * 30)
            else:
                return now
        except Exception:
            return now
