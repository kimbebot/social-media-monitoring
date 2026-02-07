#!/usr/bin/env python3
"""
Company Posts Scraper CLI
Scrape posts from LinkedIn company pages
"""

import asyncio
import json
import sys
from datetime import datetime

from loguru import logger
from src.scrapers.linkedin_company_scraper import LinkedInCompanyScraper


async def scrape_company(
    company_url: str,
    username: str,
    password: str,
    limit: int = 10,
    headless: bool = True,
    output_file: str = None,
):
    """
    Scrape posts from a single company page

    Args:
        company_url: LinkedIn company posts URL
        username: Your LinkedIn email
        password: Your LinkedIn password
        limit: Number of posts to scrape
        headless: Run in headless mode
        output_file: Optional JSON file to save results
    """
    logger.info("=" * 80)
    logger.info("LinkedIn Company Posts Scraper")
    logger.info("=" * 80)

    scraper = LinkedInCompanyScraper()

    try:
        # Initialize
        await scraper.initialize()

        # Start browser
        await scraper.start_browser(headless=headless)
        logger.info(f"Browser started (headless={headless})")

        # Login
        logger.info(f"Logging in as: {username}")
        login_success = await scraper.login(username, password)

        if not login_success:
            logger.error("Login failed. Aborting.")
            return None

        logger.success("✓ Login successful")

        # Scrape company posts
        logger.info(f"Scraping {limit} posts from: {company_url}")
        posts = await scraper.scrape_company_posts(company_url, limit=limit)

        if posts:
            logger.success(f"✓ Successfully scraped {len(posts)} posts")

            # Print summary
            print("\n" + "=" * 80)
            print(f"SCRAPED {len(posts)} POSTS")
            print("=" * 80)

            for idx, post in enumerate(posts, 1):
                print(f"\n--- Post {idx} ---")
                print(f"Company: {post['company_name']}")
                print(f"Posted: {post['posted_at_text']}")
                print(f"Content: {post['content'][:100]}...")
                print(
                    f"Likes: {post['likes_count']} | Comments: {post['comments_count']}"
                )
                print(f"URL: {post['post_url']}")

            # Save to file
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(posts, f, indent=2, ensure_ascii=False)
                logger.success(f"✓ Saved to: {output_file}")
            else:
                # Default filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                company_name = posts[0]["company_name"].replace(" ", "_")
                filename = f"company_posts_{company_name}_{timestamp}.json"

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(posts, f, indent=2, ensure_ascii=False)
                logger.success(f"✓ Saved to: {filename}")

            print("\n" + "=" * 80)
            return posts

        else:
            logger.warning("No posts found")
            return []

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return None

    finally:
        await scraper.cleanup()


async def scrape_multiple_companies(
    company_urls: list,
    username: str,
    password: str,
    limit: int = 10,
    headless: bool = True,
    output_file: str = None,
):
    """
    Scrape posts from multiple company pages
    """
    logger.info("=" * 80)
    logger.info(f"LinkedIn Company Posts Scraper - {len(company_urls)} Companies")
    logger.info("=" * 80)

    scraper = LinkedInCompanyScraper()

    try:
        # Initialize
        await scraper.initialize()

        # Start browser
        await scraper.start_browser(headless=headless)

        # Login
        logger.info(f"Logging in as: {username}")
        login_success = await scraper.login(username, password)

        if not login_success:
            logger.error("Login failed")
            return None

        logger.success("✓ Login successful")

        # Scrape all companies
        results = await scraper.scrape_multiple_companies(
            company_urls, posts_per_company=limit
        )

        # Flatten results
        all_posts = []
        for url, posts in results.items():
            all_posts.extend(posts)

        logger.success(f"✓ Total posts scraped: {len(all_posts)}")

        # Save to file
        if output_file:
            filename = output_file
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"company_posts_multiple_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "scraped_at": datetime.now().isoformat(),
                    "total_companies": len(company_urls),
                    "total_posts": len(all_posts),
                    "results": results,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        logger.success(f"✓ Saved to: {filename}")

        return results

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()
        return None

    finally:
        await scraper.cleanup()


def print_help():
    """Print help message"""
    help_text = """
LinkedIn Company Posts Scraper

Usage:
    python company_scraper.py [command] [options]

Commands:
    scrape <company_url> <email> <password> [--limit=10] [--headless] [--output=file.json]
        Scrape posts from a single company page
        
    scrape-multiple <urls_file> <email> <password> [--limit=10] [--headless] [--output=file.json]
        Scrape posts from multiple companies (one URL per line in file)

Examples:
    # Scrape IBM posts (visible browser for first time)
    python company_scraper.py scrape \\
        "https://www.linkedin.com/company/ibm/posts/?feedView=all" \\
        your@email.com \\
        yourpassword \\
        --limit=20 \\
        --no-headless
    
    # Scrape multiple companies from file
    python company_scraper.py scrape-multiple \\
        companies.txt \\
        your@email.com \\
        yourpassword \\
        --limit=10 \\
        --output=results.json

Company URL format:
    https://www.linkedin.com/company/COMPANY_NAME/posts/?feedView=all
    
    Examples:
    - https://www.linkedin.com/company/ibm/posts/?feedView=all
    - https://www.linkedin.com/company/microsoft/posts/?feedView=all
    - https://www.linkedin.com/company/google/posts/?feedView=all
"""
    print(help_text)


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()

    try:
        if command == "scrape":
            if len(sys.argv) < 5:
                print("Error: Missing arguments")
                print(
                    "Usage: python company_scraper.py scrape <company_url> <email> <password> [options]"
                )
                return

            company_url = sys.argv[2]
            username = sys.argv[3]
            password = sys.argv[4]

            # Parse options
            limit = 10
            headless = True
            output_file = None

            for arg in sys.argv[5:]:
                if arg.startswith("--limit="):
                    limit = int(arg.split("=")[1])
                elif arg == "--no-headless":
                    headless = False
                elif arg == "--headless":
                    headless = True
                elif arg.startswith("--output="):
                    output_file = arg.split("=")[1]

            await scrape_company(
                company_url, username, password, limit, headless, output_file
            )

        elif command == "scrape-multiple":
            if len(sys.argv) < 5:
                print("Error: Missing arguments")
                print(
                    "Usage: python company_scraper.py scrape-multiple <urls_file> <email> <password> [options]"
                )
                return

            urls_file = sys.argv[2]
            username = sys.argv[3]
            password = sys.argv[4]

            # Read URLs from file
            with open(urls_file, "r") as f:
                company_urls = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith("#")
                ]

            logger.info(f"Loaded {len(company_urls)} company URLs")

            # Parse options
            limit = 10
            headless = True
            output_file = None

            for arg in sys.argv[5:]:
                if arg.startswith("--limit="):
                    limit = int(arg.split("=")[1])
                elif arg == "--no-headless":
                    headless = False
                elif arg == "--headless":
                    headless = True
                elif arg.startswith("--output="):
                    output_file = arg.split("=")[1]

            await scrape_multiple_companies(
                company_urls, username, password, limit, headless, output_file
            )

        elif command == "help":
            print_help()

        else:
            print(f"Error: Unknown command '{command}'")
            print_help()

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
