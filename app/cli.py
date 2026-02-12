#!/usr/bin/env python3
"""
CLI utility for Social Media Monitor
Usage: python cli.py [command] [options]
"""

import asyncio
import sys

from loguru import logger
from sqlalchemy import func, select

from main import SocialMediaMonitor, add_account
from app.src.database.db_manager import db
from app.src.database.models import Account, Platform, Post


async def list_accounts():
    """List all accounts in database"""
    await db.init_db()

    async with db.get_session() as session:
        result = await session.execute(
            select(Account, Platform)
            .join(Platform)
            .order_by(Platform.name, Account.username)
        )

        print("\n" + "=" * 80)
        print("REGISTERED ACCOUNTS")
        print("=" * 80)

        for account, platform in result:
            status = "✓ Active" if account.is_active else "✗ Inactive"
            session_status = "✓ Valid" if account.session_valid else "✗ Expired"

            print(f"\nID: {account.id}")
            print(f"Platform: {platform.name}")
            print(f"Username: {account.username}")
            print(f"Status: {status}")
            print(f"Session: {session_status}")
            print(f"Last Login: {account.last_login_at or 'Never'}")
            print("-" * 80)


async def list_posts(platform_name=None, limit=10):
    """List recent posts"""
    await db.init_db()

    async with db.get_session() as session:
        query = select(Post).order_by(Post.posted_at.desc()).limit(limit)

        if platform_name:
            platform_result = await session.execute(
                select(Platform).where(Platform.name == platform_name)
            )
            platform = platform_result.scalar_one_or_none()
            if platform:
                query = query.where(Post.platform_id == platform.id)

        result = await session.execute(query)
        posts = result.scalars().all()

        print("\n" + "=" * 80)
        print(f"RECENT POSTS ({len(posts)})")
        print("=" * 80)

        for post in posts:
            print(f"\nAuthor: {post.author_name}")
            print(f"Posted: {post.posted_at}")
            print(f"Content: {post.content[:150]}...")
            print(f"Likes: {post.likes_count} | Comments: {post.comments_count}")
            print(f"URL: {post.post_url}")
            print("-" * 80)


async def stats():
    """Show statistics"""
    await db.init_db()

    async with db.get_session() as session:
        # Count platforms
        platforms_result = await session.execute(select(func.count(Platform.id)))
        platforms_count = platforms_result.scalar()

        # Count accounts
        accounts_result = await session.execute(select(func.count(Account.id)))
        accounts_count = accounts_result.scalar()

        # Count posts
        posts_result = await session.execute(select(func.count(Post.id)))
        posts_count = posts_result.scalar()

        # Posts by platform
        platform_stats = await session.execute(
            select(Platform.name, func.count(Post.id))
            .join(Post)
            .group_by(Platform.name)
        )

        print("\n" + "=" * 80)
        print("SYSTEM STATISTICS")
        print("=" * 80)
        print(f"\nPlatforms: {platforms_count}")
        print(f"Accounts: {accounts_count}")
        print(f"Total Posts: {posts_count}")

        print("\n" + "-" * 80)
        print("Posts by Platform:")
        print("-" * 80)
        for platform_name, count in platform_stats:
            print(f"  {platform_name}: {count} posts")

        print("\n" + "=" * 80 + "\n")


async def run_single_scraper(
    platform: str, username: str, password: str, headless: bool = True
):
    """Run a single scraper"""

    logger.info(f"Running {platform} scraper (headless={headless})")

    monitor = SocialMediaMonitor()
    await monitor.initialize()

    # Get the scraper
    if platform not in monitor.scrapers:
        logger.error(f"Scraper for {platform} not found")
        return

    scraper = monitor.scrapers[platform]

    # Override the start_browser method to use our headless setting
    original_start = scraper.start_browser

    async def start_with_headless():
        await original_start(headless=headless)

    scraper.start_browser = start_with_headless

    # Run the scraper
    stats = await scraper.run(username, password)

    logger.info("Scraper completed:")
    logger.info(f"  - Success: {stats['success']}")
    logger.info(f"  - Posts scraped: {stats['posts_scraped']}")
    logger.info(f"  - New posts: {stats['new_posts']}")
    if stats["error"]:
        logger.error(f"  - Error: {stats['error']}")


def print_help():
    """Print help message"""
    help_text = """
Social Media Monitor CLI

Usage:
    python cli.py [command] [options]

Commands:
    add-account <platform> <username> <email> <password>
        Add a new account to the database
        Example: python cli.py add-account linkedin user@email.com user@email.com mypass
    
    list-accounts
        List all registered accounts
    
    list-posts [platform] [limit]
        List recent posts (optionally filter by platform)
        Example: python cli.py list-posts linkedin 20
    
    stats
        Show system statistics
    
    scrape <platform> <username> <password> [--headless/--no-headless]
        Run scraper for specific account
        Example: python cli.py scrape linkedin user@email.com mypass --no-headless
    
    test <platform>
        Test scraper without saving (requires account in DB)
    
    help
        Show this help message

Examples:
    # Add account
    python cli.py add-account linkedin john@email.com john@email.com SecretPass123
    
    # Run scraper in non-headless mode (for debugging)
    python cli.py scrape linkedin john@email.com SecretPass123 --no-headless
    
    # View recent posts
    python cli.py list-posts linkedin 50
    
    # Check stats
    python cli.py stats
"""
    print(help_text)


async def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1].lower()

    try:
        if command == "add-account":
            if len(sys.argv) < 6:
                print("Error: Missing arguments")
                print(
                    "Usage: python cli.py add-account <platform> <username> <email> <password>"
                )
                return

            platform = sys.argv[2]
            username = sys.argv[3]
            email = sys.argv[4]
            password = sys.argv[5]

            await add_account(platform, username, email, password)

        elif command == "list-accounts":
            await list_accounts()

        elif command == "list-posts":
            platform = sys.argv[2] if len(sys.argv) > 2 else None
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            await list_posts(platform, limit)

        elif command == "stats":
            await stats()

        elif command == "scrape":
            if len(sys.argv) < 5:
                print("Error: Missing arguments")
                print(
                    "Usage: python cli.py scrape <platform> <username> <password> [--headless/--no-headless]"
                )
                return

            platform = sys.argv[2]
            username = sys.argv[3]
            password = sys.argv[4]
            headless = "--no-headless" not in sys.argv

            await run_single_scraper(platform, username, password, headless)

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
