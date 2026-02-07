"""
LinkedIn Company Posts Scraper
Scrapes posts from specific company pages
"""

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from src.utils.stealth import HumanBehavior

from .base_scraper import BaseScraper


class LinkedInCompanyScraper(BaseScraper):
    """Scrape posts from specific LinkedIn company pages"""

    def __init__(self):
        super().__init__("linkedin")
        self.company_urls = []  # List of company URLs to scrape

    def get_base_url(self) -> str:
        return "https://www.linkedin.com"

    def add_company_url(self, url: str):
        """Add a company URL to scrape"""
        if url not in self.company_urls:
            self.company_urls.append(url)
            logger.info(f"Added company URL: {url}")

    async def perform_login(self, username: str, password: str) -> bool:
        """Login to LinkedIn"""
        try:
            # Navigate to LinkedIn
            await self.page.goto(
                "https://www.linkedin.com/login", wait_until="networkidle"
            )
            await HumanBehavior.random_delay(2, 4)

            # Check if already on "select account" screen
            current_url = self.page.url
            if "account" in current_url.lower() or "select" in current_url.lower():
                logger.warning("⚠️  Account selection screen detected!")
                logger.info("Attempting to auto-select your account...")

                if await self._handle_account_selection():
                    return True

                logger.info("⏳ Please select your account manually in the browser")
                logger.info("⏳ Waiting up to 2 minutes...")

                for i in range(12):  # 2 minutes
                    await HumanBehavior.random_delay(8, 12)
                    current_url = self.page.url

                    if (
                        "feed" in current_url
                        or "mynetwork" in current_url
                        or "company" in current_url
                    ):
                        logger.success("✅ Account selected and logged in!")
                        return True

                    if "login" not in current_url and "account" not in current_url:
                        logger.success("✅ Navigation completed")
                        return True

                    if i % 3 == 0:
                        logger.info(f"⏳ Still waiting... ({(i + 1) * 10} seconds)")

                # Check if we ended up logged in anyway
                current_url = self.page.url
                if "login" not in current_url:
                    return True

            # Type username with human-like behavior
            try:
                await HumanBehavior.human_type(self.page, "input#username", username)
                await HumanBehavior.micro_sleep()

                # Type password
                await HumanBehavior.human_type(self.page, "input#password", password)
                await HumanBehavior.random_delay(1, 2)

                # Click login button
                await self.page.click('button[type="submit"]')
            except Exception as e:
                logger.warning(
                    f"Could not type credentials (might already be logged in): {e}"
                )

            # Wait a moment to see what happens
            await HumanBehavior.random_delay(3, 5)

            # Check current state
            current_url = self.page.url

            # Check for account selection screen AFTER login
            if "account" in current_url.lower() or "select" in current_url.lower():
                logger.warning("⚠️  Account selection screen appeared after login!")
                logger.info("Attempting to auto-select your account...")

                if await self._handle_account_selection():
                    return True

                logger.info("⏳ Please select your account in the browser")
                logger.info("⏳ Waiting up to 2 minutes...")

                for i in range(12):
                    await HumanBehavior.random_delay(8, 12)
                    current_url = self.page.url

                    if (
                        "feed" in current_url
                        or "mynetwork" in current_url
                        or "company" in current_url
                    ):
                        logger.success("✅ Account selected!")
                        return True

                    if i % 3 == 0:
                        logger.info(f"⏳ Still waiting... ({(i + 1) * 10} seconds)")

            # Check if CAPTCHA appeared
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

                    if (
                        "feed" in current_url
                        or "mynetwork" in current_url
                        or "company" in current_url
                    ):
                        logger.success("✅ Login successful after CAPTCHA!")
                        return True

                    if i % 3 == 0:
                        logger.info(
                            f"⏳ Still waiting... ({(i + 1) * 10} seconds elapsed)"
                        )

            # Wait for navigation
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            await HumanBehavior.random_delay(2, 3)

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
                for i in range(30):
                    await HumanBehavior.random_delay(8, 12)
                    current_url = self.page.url

                    if "feed" in current_url or "mynetwork" in current_url:
                        logger.success("Security checkpoint completed! Proceeding...")
                        return True

                    if i % 3 == 0:
                        logger.info(
                            f"Still waiting... ({(i + 1) * 10} seconds elapsed)"
                        )

                # Final check
                return "feed" in self.page.url
            else:
                # Check if we're already logged in somewhere
                if "linkedin.com" in current_url and "login" not in current_url:
                    logger.success("Already logged in!")
                    return True

                logger.error(f"Login failed, redirected to: {current_url}")
                return False

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False

    async def verify_session(self) -> bool:
        """Verify LinkedIn session is valid"""
        try:
            await self.page.goto("https://www.linkedin.com/feed/", timeout=15000)
            await HumanBehavior.random_delay(2, 3)

            current_url = self.page.url
            if "account" in current_url.lower() or "select" in current_url.lower():
                if await self._handle_account_selection():
                    await HumanBehavior.random_delay(2, 3)
                    current_url = self.page.url

            if "feed" in current_url or "company" in current_url:
                logger.info("Session is valid")
                return True

            return False
        except Exception:
            return False

    async def _captcha_present(self) -> bool:
        """Check if CAPTCHA is present on page"""
        try:
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

    async def scrape_company_posts(
        self, company_url: str, limit: int = 10
    ) -> List[Dict]:
        """
        Scrape posts from a specific company page

        Args:
            company_url: URL like https://www.linkedin.com/company/ibm/posts/?feedView=all
            limit: Number of posts to scrape (default 10)

        Returns:
            List of post dictionaries
        """
        logger.info(f"Scraping company posts from: {company_url}")
        posts = []

        try:
            # Navigate to company posts page using existing session only
            logger.info("Navigating to company page...")
            if not await self._navigate_with_session(company_url):
                logger.error("Session not accepted by LinkedIn; aborting without login")
                return []
            await HumanBehavior.random_delay(3, 5)

            logger.info(f"✓ Arrived at: {self.page.url}")

            # Detect direct post URL and handle separately
            if self._is_post_url(self.page.url):
                logger.info("Detected direct post URL, extracting single post...")
                post_elements = await self._find_post_elements()
                if post_elements:
                    company_name = await self._extract_company_name()
                    post_data = await self._extract_company_post_data(
                        post_elements[0], company_name, company_url
                    )
                    return [post_data] if post_data else []
                logger.warning("Could not locate post element on permalink page")
                return []

            # Extract company name from URL or page
            company_name = await self._extract_company_name()
            logger.info(f"✓ Company: {company_name}")

            # Scroll to load posts
            logger.info("Scrolling to load posts...")
            for scroll in range(5):  # Scroll 5 times to load more posts
                logger.debug(f"Scroll {scroll + 1}/5")
                await HumanBehavior.human_scroll(self.page, scrolls=2)
                await HumanBehavior.random_delay(2, 4)

            logger.info("✓ Scrolling complete")

            logger.info("Looking for post elements...")
            post_elements = await self._find_post_elements()

            if not post_elements:
                logger.warning("⚠️  No posts found with standard selectors")
                logger.info("Taking screenshot for debugging...")

                # Take screenshot
                screenshot_file = (
                    f"debug_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                )
                await self.page.screenshot(path=screenshot_file, full_page=True)
                logger.info(f"📸 Saved screenshot to: {screenshot_file}")

                # Save page content for debugging
                logger.info("Saving page HTML for debugging...")
                content = await self.page.content()
                debug_file = (
                    f"debug_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                )
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"📄 Saved page HTML to: {debug_file}")
                logger.info("   Check this file to see what LinkedIn is showing")

                # Try one more time with ANY div that might be a post
                logger.info("Attempting to find ANY post-like elements...")
                all_divs = await self.page.query_selector_all("div")
                logger.info(f"Found {len(all_divs)} total div elements on page")

                # Look for divs with substantial content
                for div in all_divs[:50]:  # Check first 50
                    try:
                        text = await div.inner_text()
                        if len(text) > 100:  # Likely a post if it has substantial text
                            post_elements.append(div)
                            if len(post_elements) >= limit:
                                break
                    except:
                        continue

                if post_elements:
                    logger.info(
                        f"Found {len(post_elements)} potential post elements by content length"
                    )

            if not post_elements:
                logger.error("❌ Could not find any post elements")
                logger.error("Possible reasons:")
                logger.error("  1. LinkedIn changed their HTML structure")
                logger.error("  2. Page didn't load completely")
                logger.error("  3. You're not logged in properly")
                logger.error("  4. Company has no posts")
                logger.error("  5. Check the debug HTML file for details")
                return []

            logger.info(f"Processing up to {min(limit, len(post_elements))} posts...")

            # Extract data from posts
            for idx, post_element in enumerate(post_elements[:limit]):
                try:
                    logger.debug(f"Extracting post {idx + 1}...")
                    post_data = await self._extract_company_post_data(
                        post_element, company_name, company_url
                    )
                    if post_data:
                        posts.append(post_data)
                        logger.success(
                            f"✓ Extracted post {idx + 1}/{min(limit, len(post_elements))}: {post_data['content'][:50]}..."
                        )
                    else:
                        logger.warning(f"⚠️  Post {idx + 1} returned no data")

                    # Random micro-pause
                    if idx % 3 == 0:
                        await HumanBehavior.micro_sleep()

                except Exception as e:
                    logger.warning(f"❌ Error extracting post {idx + 1}: {str(e)}")
                    continue

            if posts:
                logger.success(
                    f"✅ Successfully scraped {len(posts)} posts from {company_name}"
                )
            else:
                logger.error("❌ No posts were successfully extracted")

        except Exception as e:
            logger.error(f"Error scraping company posts: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())

        return posts

    async def _extract_company_name(self) -> str:
        """Extract company name from the page"""
        try:
            # Try different selectors for company name
            selectors = [
                "h1.org-top-card-summary__title",
                'h1[class*="org-top-card"]',
                ".organization-outlet__name",
                "h1",
            ]

            for selector in selectors:
                element = await self.page.query_selector(selector)
                if element:
                    name = await element.inner_text()
                    if name and len(name) > 0:
                        return name.strip()

            # Fallback: extract from URL
            url = self.page.url
            if "/company/" in url:
                company_slug = url.split("/company/")[1].split("/")[0]
                return company_slug.replace("-", " ").title()

            return "Unknown Company"

        except Exception:
            return "Unknown Company"

    async def _extract_company_post_data(
        self, post_element, company_name: str, company_url: str
    ) -> Optional[Dict]:
        """Extract data from a single company post element"""
        try:
            # Expand "see more" to capture full text
            await self._expand_post_text(post_element)

            # Post ID
            post_urn = await post_element.get_attribute("data-urn")
            if not post_urn:
                post_urn = await post_element.get_attribute("data-id")

            if not post_urn:
                # Try to get from link
                link_element = await post_element.query_selector('a[href*="update"]')
                if link_element:
                    href = await link_element.get_attribute("href")
                    if href and "update" in href:
                        post_urn = href.split("/")[-1].split("?")[0]

            if not post_urn:
                logger.debug("No post URN found, skipping")
                return None

            # Post content/text
            content_selectors = [
                "div.feed-shared-update-v2__description",
                "div.feed-shared-update-v2__commentary",
                "div.update-components-text",
                "div.update-components-text__commentary",
                "span.update-components-text__text-view",
                "div.feed-shared-inline-show-more-text",
                'div[class*="update-components-text"]',
                'span[dir="ltr"]',
            ]

            content = ""
            for selector in content_selectors:
                content_element = await post_element.query_selector(selector)
                if content_element:
                    content = await content_element.inner_text()
                    if content:
                        break

            # Post URL
            post_url = f"https://www.linkedin.com/feed/update/{post_urn}"
            link_element = await post_element.query_selector('a[href*="update"]')
            if link_element:
                href = await link_element.get_attribute("href")
                if href:
                    post_url = (
                        href
                        if href.startswith("http")
                        else f"https://www.linkedin.com{href}"
                    )

            # Timestamp
            time_selectors = [
                "span.update-components-actor__sub-description",
                "time",
                'span[class*="visually-hidden"]',
            ]

            posted_at_text = None
            for selector in time_selectors:
                time_element = await post_element.query_selector(selector)
                if time_element:
                    posted_at_text = await time_element.inner_text()
                    if posted_at_text:
                        break

            posted_at = (
                self._parse_linkedin_time(posted_at_text)
                if posted_at_text
                else datetime.utcnow()
            )

            # Engagement metrics
            likes_count = 0
            comments_count = 0
            shares_count = 0

            # Likes/reactions
            reaction_selectors = [
                "span.social-details-social-counts__reactions-count",
                'button[aria-label*="reaction"]',
                'span[class*="reactions-count"]',
            ]

            for selector in reaction_selectors:
                likes_element = await post_element.query_selector(selector)
                if likes_element:
                    likes_text = await likes_element.inner_text()
                    likes_count = self._parse_engagement_count(likes_text)
                    if likes_count > 0:
                        break

            # Comments
            comment_selectors = [
                'button[aria-label*="comment"]',
                'span[class*="comments-count"]',
            ]

            for selector in comment_selectors:
                comments_element = await post_element.query_selector(selector)
                if comments_element:
                    comments_text = await comments_element.inner_text()
                    comments_count = self._parse_engagement_count(comments_text)
                    if comments_count > 0:
                        break

            # Media (images/videos)
            media = []
            media_elements = await post_element.query_selector_all(
                'img[src*="media"], video'
            )
            for media_elem in media_elements[:3]:  # Max 3 media items
                try:
                    tag_name = await media_elem.evaluate("el => el.tagName")
                    if tag_name.lower() == "img":
                        src = await media_elem.get_attribute("src")
                        if src and "media" in src:
                            media.append({"type": "image", "url": src})
                    elif tag_name.lower() == "video":
                        src = await media_elem.get_attribute("src")
                        if src:
                            media.append({"type": "video", "url": src})
                except Exception:
                    pass

            return {
                "post_id": post_urn,
                "company_name": company_name,
                "company_url": company_url,
                "post_url": post_url,
                "content": content.strip(),
                "posted_at": posted_at.isoformat(),
                "posted_at_text": posted_at_text,
                "likes_count": likes_count,
                "comments_count": comments_count,
                "shares_count": shares_count,
                "media": media,
                "scraped_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.debug(f"Error in _extract_company_post_data: {str(e)}")
            return None

    def _parse_engagement_count(self, text: str) -> int:
        """Parse engagement count from text"""
        try:
            if not text:
                return 0

            text = text.strip().replace(",", "").replace(" ", "")

            if "K" in text.upper():
                return int(float(text.upper().replace("K", "")) * 1000)
            elif "M" in text.upper():
                return int(float(text.upper().replace("M", "")) * 1000000)
            else:
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
            elif "minute" in time_text or "min" in time_text:
                minutes = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(minutes=minutes)
            elif "hour" in time_text or "hr" in time_text or "h" == time_text[-1]:
                hours = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(hours=hours)
            elif "day" in time_text or "d" == time_text[-1]:
                days = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(days=days)
            elif "week" in time_text or "wk" in time_text or "w" == time_text[-1]:
                weeks = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(weeks=weeks)
            elif "month" in time_text or "mo" in time_text:
                months = int("".join(filter(str.isdigit, time_text)))
                return now - timedelta(days=months * 30)
            else:
                return now
        except Exception:
            return now

    async def scrape_feed(self) -> List[Dict]:
        """Override - not used for company scraping"""
        return []

    def _is_post_url(self, url: str) -> bool:
        """Detect if the URL points to a single post"""
        url = (url or "").lower()
        return "/feed/update/" in url or "/posts/" in url or "urn:li:activity" in url

    async def _find_post_elements(self) -> List:
        """Find post elements on the page using multiple selectors"""
        post_selectors = [
            "div.feed-shared-update-v2",
            'div[data-urn*="urn:li:activity"]',
            'div[data-id*="urn:li:activity"]',
            'li[class*="profile-creator-shared-feed-update"]',
            'div[class*="occludable-update"]',
            "article",
            "div[data-urn]",
        ]

        for selector in post_selectors:
            logger.debug(f"Trying selector: {selector}")
            elements = await self.page.query_selector_all(selector)
            if elements and len(elements) > 0:
                logger.success(f"✓ Found {len(elements)} elements using: {selector}")
                return elements
            logger.debug(f"  No elements found with: {selector}")

        return []

    async def _expand_post_text(self, post_element):
        """Click 'See more' within a post if present"""
        see_more_selectors = [
            'button[aria-label*="See more"]',
            'button[aria-label*="see more"]',
            'button[aria-expanded="false"]',
        ]

        for selector in see_more_selectors:
            try:
                btn = await post_element.query_selector(selector)
                if btn:
                    await btn.click()
                    await HumanBehavior.micro_sleep()
                    return
            except Exception:
                continue

    async def _handle_account_selection(self) -> bool:
        """Attempt to auto-select the correct LinkedIn account"""
        try:
            # Specific LinkedIn "choose account" screen
            try:
                await self.page.wait_for_selector(
                    'div[class="artdeco-list artdeco-list--border"]', timeout=10000
                )
                await self.page.wait_for_selector(
                    'div[class="member-profile-container list-box"]', timeout=10000
                )

                first_item_locator = self.page.locator(
                    'div[class="member-profile-container list-box"]'
                ).first
                await first_item_locator.scroll_into_view_if_needed()

                # Prefer the clickable button within the item
                details_button = first_item_locator.locator(
                    'button.member-profile__details'
                )
                if await details_button.count() > 0:
                    await details_button.first.click(timeout=8000, force=True)
                else:
                    await first_item_locator.click(timeout=8000, force=True)
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                return True
            except Exception:
                pass

            # Fallback: when /uas/login shows the account list
            try:
                await self.page.wait_for_selector(
                    "button.member-profile__details", timeout=10000
                )
                details_button = self.page.locator(
                    "button.member-profile__details"
                ).first
                await details_button.scroll_into_view_if_needed()
                await details_button.click(timeout=8000, force=True)
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                return True
            except Exception:
                pass

            identifiers = []
            if self.account:
                if self.account.email:
                    identifiers.append(self.account.email)
                if self.account.username and self.account.username not in identifiers:
                    identifiers.append(self.account.username)

            # Try to click a matching account card by text
            for identifier in identifiers:
                if not identifier:
                    continue
                locator = self.page.locator(f"text={identifier}")
                if await locator.count() > 0:
                    try:
                        await locator.first.click(timeout=5000)
                        await self.page.wait_for_load_state(
                            "networkidle", timeout=15000
                        )
                        return True
                    except Exception:
                        pass

            # Fallback: if only one account option, click it
            account_selectors = [
                "li.account-item",
                "div.account-item",
                "button.account-item",
                "li[class*='account']",
                "button[class*='account']",
                "a[class*='account']",
            ]

            for selector in account_selectors:
                elements = await self.page.query_selector_all(selector)
                if elements and len(elements) == 1:
                    try:
                        await elements[0].click()
                        await self.page.wait_for_load_state(
                            "networkidle", timeout=15000
                        )
                        return True
                    except Exception:
                        continue

            return False
        except Exception:
            return False

    async def _navigate_with_session(self, target_url: str) -> bool:
        """
        Navigate to target URL using existing session only.
        If redirected to account selection, auto-select and return to target.
        Do not perform credential login here.
        """
        try:
            await self.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(2, 3)

            current_url = self.page.url or ""
            lower_url = current_url.lower()
            redirect_url = self._extract_session_redirect(current_url) or target_url

            # If redirected to account selection, try to pick first account
            if "account" in lower_url or "select" in lower_url:
                logger.info("Account selection detected; attempting to select account")
                if await self._handle_account_selection():
                    await HumanBehavior.random_delay(2, 3)
                    await self.page.goto(
                        redirect_url, wait_until="domcontentloaded", timeout=30000
                    )
                    return True

            # Authwall can appear even with session; try account selection then retry
            if "authwall" in lower_url:
                logger.info("Authwall detected; attempting to select account")
                if await self._handle_account_selection():
                    await HumanBehavior.random_delay(2, 3)
                    await self.page.goto(
                        redirect_url, wait_until="domcontentloaded", timeout=30000
                    )
                    return True

            # If redirected to login, session is invalid; do not login
            if "linkedin.com/login" in lower_url:
                logger.warning(f"Redirected to login: {current_url}")
                return False

            return True
        except Exception as e:
            logger.warning(f"Navigation error: {str(e)}")
            return False

    def _extract_session_redirect(self, url: str) -> Optional[str]:
        """Extract sessionRedirect target from authwall URL if present."""
        try:
            from urllib.parse import urlparse, parse_qs, unquote

            if "sessionRedirect=" not in url:
                return None
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            redirect_vals = qs.get("sessionRedirect")
            if not redirect_vals:
                return None
            return unquote(redirect_vals[0])
        except Exception:
            return None

    async def scrape_multiple_companies(
        self, company_urls: List[str], posts_per_company: int = 10
    ) -> Dict[str, List[Dict]]:
        """
        Scrape posts from multiple company pages

        Args:
            company_urls: List of company post URLs
            posts_per_company: Number of posts to scrape per company

        Returns:
            Dictionary mapping company URL to list of posts
        """
        results = {}

        for idx, url in enumerate(company_urls):
            logger.info(f"Scraping company {idx + 1}/{len(company_urls)}: {url}")

            try:
                posts = await self.scrape_company_posts(url, limit=posts_per_company)
                results[url] = posts

                # Delay between companies
                if idx < len(company_urls) - 1:
                    delay = 15 + (idx * 5)  # Increasing delay
                    logger.info(f"Waiting {delay} seconds before next company...")
                    await HumanBehavior.random_delay(delay, delay + 5)

            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                results[url] = []

        return results
