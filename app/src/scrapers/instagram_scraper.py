"""
Instagram profile scraper
Scrapes recent posts from a profile page.
"""
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from app.src.utils.stealth import HumanBehavior
from .base_scraper import BaseScraper


class InstagramScraper(BaseScraper):
    """Scrape posts from Instagram profiles"""

    def __init__(self):
        super().__init__("instagram")

    def get_base_url(self) -> str:
        return "https://www.instagram.com"

    async def perform_login(self, username: str, password: str) -> bool:
        """Login to Instagram (best effort; prefers session reuse)."""
        try:
            await self.page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
            await HumanBehavior.random_delay(2, 3)

            try:
                await HumanBehavior.human_type(self.page, 'input[name="username"]', username)
                await HumanBehavior.human_type(self.page, 'input[name="password"]', password)
                await HumanBehavior.random_delay(1, 2)
                await self.page.locator('button[type="submit"]').first.click()
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
        """Verify Instagram session."""
        try:
            await self.page.goto("https://www.instagram.com/", timeout=15000)
            await HumanBehavior.random_delay(2, 3)
            current_url = self.page.url.lower()
            if "login" in current_url:
                return False
            # Detect login wall or login form even when URL is not /accounts/login/
            login_form = await self.page.query_selector('input[name="username"], input[name="password"]')
            if login_form:
                return False
            login_button = await self.page.query_selector('button:has-text("Log in"), a:has-text("Log in")')
            if login_button:
                return False
            return True
        except Exception:
            return False

    async def scrape_feed(self) -> List[Dict]:
        return []

    async def scrape_profile_posts(self, profile_url: str, limit: int = 5) -> List[Dict]:
        logger.info(f"Scraping Instagram profile posts from: {profile_url}")
        posts: List[Dict] = []

        try:
            if self._is_post_url(profile_url):
                resolved = await self._resolve_profile_url_from_post(profile_url)
                if resolved:
                    profile_url = resolved

            await self.page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(2, 3)
            try:
                await self.page.wait_for_selector(
                    'a[href*="/p/"], a[href*="/reel/"]',
                    timeout=15000,
                )
            except Exception:
                pass

            target_limit = None if limit <= 0 else limit
            seen = await self._collect_post_links(target_limit)

            for post_url in seen:
                if target_limit and len(posts) >= target_limit:
                    break
                if await self.post_url_exists(post_url):
                    logger.info(
                        f"Encountered existing Instagram post URL; stopping scan for {profile_url}"
                    )
                    break
                post_id = post_url.split("/p/")[-1].split("/")[0]
                if "/reel/" in post_url:
                    post_id = post_url.split("/reel/")[-1].split("/")[0]
                detail = await self._scrape_post_detail(post_url)
                posts.append(
                    {
                        "post_id": post_id,
                        "company_name": detail.get("author_name"),
                        "company_url": profile_url,
                        "post_url": post_url,
                        "content": detail.get("content") or "",
                        "posted_at": detail.get("posted_at") or datetime.utcnow().isoformat(),
                        "posted_at_text": None,
                        "likes_count": detail.get("likes_count", 0),
                        "comments_count": detail.get("comments_count", 0),
                        "shares_count": 0,
                        "media": detail.get("media", []),
                        "scraped_at": datetime.utcnow().isoformat(),
                    }
                )
                await HumanBehavior.random_delay(1.5, 3.0)

            logger.success(f"✓ Scraped {len(posts)} posts from Instagram profile")
        except Exception as e:
            logger.error(f"Error scraping Instagram profile: {e}")

        return posts

    async def _scrape_post_detail(self, post_url: str) -> Dict:
        """Open a post URL and extract caption/content."""
        data: Dict = {"content": "", "posted_at": None, "likes_count": 0, "comments_count": 0, "media": []}
        try:
            await self.page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(1.5, 2.5)
            try:
                await self.page.wait_for_selector("article", timeout=15000)
            except Exception:
                pass

            await self._expand_caption_if_needed()

            author_el = await self.page.query_selector('header a[role="link"]')
            if author_el:
                data["author_name"] = await author_el.inner_text()

            data["content"] = await self._extract_caption_text(data.get("author_name"))

            # Posted time
            time_el = await self.page.query_selector("time")
            if time_el:
                dt = await time_el.get_attribute("datetime")
                if dt:
                    data["posted_at"] = dt

            return data
        except Exception as e:
            logger.warning(f"Instagram post detail failed: {e}")
            return data

    async def _expand_caption_if_needed(self) -> None:
        try:
            more_button = self.page.locator("article button").filter(has_text="more")
            if await more_button.count() > 0:
                await more_button.first.click()
                await HumanBehavior.random_delay(0.5, 1.0)
                return
            more_button = self.page.locator("article button").filter(has_text="see more")
            if await more_button.count() > 0:
                await more_button.first.click()
                await HumanBehavior.random_delay(0.5, 1.0)
                return
            more_button = self.page.locator("article span").filter(has_text="more")
            if await more_button.count() > 0:
                await more_button.first.click()
                await HumanBehavior.random_delay(0.5, 1.0)
        except Exception:
            return

    async def _extract_caption_text(self, author_name: Optional[str] = None) -> str:
        try:
            text = await self.page.evaluate(
                """
                (author) => {
                  const collectCandidates = () => {
                    const candidates = [];
                    const extract = (el) => {
                      if (!el) return "";
                      const walk = (node) => {
                        let text = "";
                        node.childNodes.forEach((child) => {
                          if (child.nodeType === Node.TEXT_NODE) {
                            text += child.textContent;
                          } else if (child.nodeName === "BR") {
                            text += "\\n";
                          } else {
                            text += walk(child);
                          }
                        });
                        return text;
                      };
                      return walk(el).trim();
                    };

                    const article = document.querySelector("article");
                    if (article) {
                      const listItems = Array.from(article.querySelectorAll("ul > li"));
                      for (const li of listItems) {
                        const authorLink = li.querySelector('a[role="link"]');
                        const authorText = authorLink ? authorLink.textContent.trim() : "";
                        if (author && authorText && authorText !== author) {
                          continue;
                        }
                        const spans = Array.from(li.querySelectorAll("span[dir='auto']"));
                        if (spans.length > 0) {
                          const parts = [];
                          for (const span of spans) {
                            const part = extract(span);
                            if (part) parts.push(part);
                          }
                          if (parts.length > 0) {
                            candidates.push(parts.join("\\n").trim());
                          }
                        }
                      }
                    }

                    const selectors = [
                      "article div[role='presentation'] span[dir='auto']",
                      "article span[dir='auto']",
                      "article span.x13faqbe",
                      "article h1",
                    ];
                    for (const sel of selectors) {
                      const nodes = Array.from(document.querySelectorAll(sel));
                      for (const node of nodes) {
                        const t = extract(node);
                        if (t) candidates.push(t);
                      }
                    }
                    return candidates;
                  };

                  const fromLdJson = () => {
                    const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                    const candidates = [];
                    for (const script of scripts) {
                      try {
                        const data = JSON.parse(script.textContent || "");
                        const items = Array.isArray(data) ? data : [data];
                        for (const item of items) {
                          if (!item || typeof item !== "object") continue;
                          const desc = item.description || item.caption || "";
                          if (desc && typeof desc === "string") {
                            candidates.push(desc);
                          }
                          if (item.mainEntityOfPage && typeof item.mainEntityOfPage === "object") {
                            const d = item.mainEntityOfPage.description || "";
                            if (d) candidates.push(d);
                          }
                        }
                      } catch (e) {
                        continue;
                      }
                    }
                    if (candidates.length === 0) return "";
                    candidates.sort((a, b) => b.length - a.length);
                    return candidates[0].trim();
                  };

                  const candidates = collectCandidates();
                  if (candidates.length > 0) {
                    candidates.sort((a, b) => b.length - a.length);
                    return candidates[0];
                  }

                  const container = document.querySelector("div.x9f619.xh8yej3.x1l90r2v");
                  if (container) {
                    const divs = Array.from(container.querySelectorAll(":scope > div"));
                    if (divs.length > 0) {
                      const captionDiv = divs[0];
                      const text = captionDiv ? captionDiv.innerText.trim() : "";
                      if (text) return text;
                    }
                  }

                  const ld = fromLdJson();
                  if (ld) return ld;
                  return "";
                }
                """,
                author_name or None,
            )
            if text:
                return text
            try:
                debug_candidates = await self.page.evaluate(
                    """
                    () => {
                      const extract = (el) => {
                        if (!el) return "";
                        const walk = (node) => {
                          let text = "";
                          node.childNodes.forEach((child) => {
                            if (child.nodeType === Node.TEXT_NODE) {
                              text += child.textContent;
                            } else if (child.nodeName === "BR") {
                              text += "\\n";
                            } else {
                              text += walk(child);
                            }
                          });
                          return text;
                        };
                        return walk(el).trim();
                      };
                      const selectors = [
                        "article div[role='presentation'] span[dir='auto']",
                        "article span[dir='auto']",
                        "article span.x13faqbe",
                        "article h1",
                      ];
                      const candidates = [];
                      for (const sel of selectors) {
                        const nodes = Array.from(document.querySelectorAll(sel));
                        for (const node of nodes) {
                          const t = extract(node);
                          if (t) candidates.push(t);
                        }
                      }
                      candidates.sort((a, b) => b.length - a.length);
                      return candidates.slice(0, 3).map((t) => t.length);
                    }
                    """
                )
                logger.warning(f"Instagram caption candidates lengths: {debug_candidates}")
            except Exception:
                pass
            ld_text = await self.page.evaluate(
                """
                () => {
                  const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                  const candidates = [];
                  for (const script of scripts) {
                    try {
                      const data = JSON.parse(script.textContent || "");
                      const items = Array.isArray(data) ? data : [data];
                      for (const item of items) {
                        if (!item || typeof item !== "object") continue;
                        const desc = item.description || item.caption || "";
                        if (desc && typeof desc === "string") {
                          candidates.push(desc);
                        }
                      }
                    } catch (e) {
                      continue;
                    }
                  }
                  if (candidates.length === 0) return "";
                  candidates.sort((a, b) => b.length - a.length);
                  return candidates[0].trim();
                }
                """
            )
            if ld_text:
                return ld_text
            meta = await self.page.query_selector('meta[property="og:description"]')
            if meta:
                content = await meta.get_attribute("content")
                if content:
                    return content.strip()
            return ""
        except Exception:
            return ""

    async def _resolve_profile_url_from_post(self, post_url: str) -> Optional[str]:
        try:
            await self.page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
            await HumanBehavior.random_delay(1.5, 2.5)
            profile_link = await self.page.query_selector('header a[role="link"]')
            if not profile_link:
                return None
            href = await profile_link.get_attribute("href")
            if not href:
                return None
            if href.startswith("http"):
                return href
            return f"https://www.instagram.com{href}"
        except Exception:
            return None

    @staticmethod
    def _is_post_url(url: str) -> bool:
        lowered = url.lower()
        return "/p/" in lowered or "/reel/" in lowered or "/tv/" in lowered

    async def _collect_post_links(self, target_limit: Optional[int]) -> List[str]:
        max_scrolls = 30
        stable_rounds = 0
        seen: List[str] = []
        seen_set = set()

        for _ in range(max_scrolls):
            links = await self.page.query_selector_all('a[href*="/p/"], a[href*="/reel/"]')
            new_found = 0
            for link in links:
                href = await link.get_attribute("href")
                if not href:
                    continue
                post_url = href if href.startswith("http") else f"https://www.instagram.com{href}"
                if post_url in seen_set:
                    continue
                if await self.post_url_exists(post_url):
                    logger.info("Encountered existing Instagram post URL during link scan; stopping early")
                    return seen
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
