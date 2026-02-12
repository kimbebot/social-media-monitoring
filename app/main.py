"""
Social Media Monitor - Main Application
"""
import asyncio
import sys
from loguru import logger
from datetime import datetime

from app.src.database.db_manager import db
from app.src.scrapers.linkedin_scraper import LinkedInScraper
from app.src.utils.encryption import encryption
from app.config.settings import settings


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    settings.log_file,
    rotation="10 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level=settings.log_level
)


class SocialMediaMonitor:
    """Main application orchestrator"""
    
    def __init__(self):
        self.scrapers = {}
    
    async def initialize(self):
        """Initialize application"""
        logger.info("="*60)
        logger.info("Social Media Monitor - Initializing")
        logger.info("="*60)
        
        # Initialize database
        await db.init_db()
        logger.success("Database initialized")
        
        # Initialize scrapers
        if settings.linkedin_enabled:
            self.scrapers['linkedin'] = LinkedInScraper()
            logger.info("LinkedIn scraper enabled")
        
        # Add more scrapers here as they're implemented
        # if settings.facebook_enabled:
        #     self.scrapers['facebook'] = FacebookScraper()
        # if settings.twitter_enabled:
        #     self.scrapers['twitter'] = TwitterScraper()
    
    async def run_scraper(self, platform: str, username: str, password: str):
        """Run a specific scraper"""
        if platform not in self.scrapers:
            logger.error(f"Scraper for {platform} not found or not enabled")
            return
        
        logger.info(f"Starting {platform} scraper for user: {username}")
        scraper = self.scrapers[platform]
        
        stats = await scraper.run(username, password)
        
        logger.info(f"{platform} scraper completed:")
        logger.info(f"  - Success: {stats['success']}")
        logger.info(f"  - Posts scraped: {stats['posts_scraped']}")
        logger.info(f"  - New posts: {stats['new_posts']}")
        if stats['error']:
            logger.error(f"  - Error: {stats['error']}")
    
    async def run_all_scrapers(self):
        """Run all enabled scrapers"""
        logger.info("Running all scrapers...")
        
        # Get all active accounts from database
        platforms = await db.get_active_platforms()
        
        for platform in platforms:
            logger.info(f"Processing {platform.name}...")
            # Get accounts for this platform
            # This would need to be implemented based on your needs
            # For now, you'll need to manually call run_scraper with credentials
        
        logger.success("All scrapers completed")


async def add_account(platform: str, username: str, email: str, password: str):
    """Add a new account to the database"""
    logger.info(f"Adding account: {username} for platform: {platform}")
    
    # Initialize database
    await db.init_db()
    
    # Get or create platform
    platform_obj = await db.get_or_create_platform(
        name=platform,
        base_url=f"https://www.{platform}.com"
    )
    
    # Encrypt password
    encrypted_password = encryption.encrypt(password)
    
    # Create account
    account = await db.create_account(
        platform_id=platform_obj.id,
        username=username,
        email=email,
        password_encrypted=encrypted_password
    )
    
    logger.success(f"Account added successfully with ID: {account.id}")
    return account


async def test_scraper(platform: str, username: str, password: str):
    """Test a scraper with credentials"""
    monitor = SocialMediaMonitor()
    await monitor.initialize()
    await monitor.run_scraper(platform, username, password)


async def main():
    """Main entry point"""
    # Example usage:
    
    # 1. Add account (do this once)
    # await add_account(
    #     platform="linkedin",
    #     username="your_email@example.com",
    #     email="your_email@example.com",
    #     password="your_password"
    # )
    
    # 2. Test scraper
    # await test_scraper(
    #     platform="linkedin",
    #     username="your_email@example.com",
    #     password="your_password"
    # )
    
    # 3. Or use the full monitor
    monitor = SocialMediaMonitor()
    await monitor.initialize()
    
    logger.info("Social Media Monitor ready!")
    logger.info("Next steps:")
    logger.info("1. Add your accounts using add_account()")
    logger.info("2. Run scrapers using monitor.run_scraper()")
    logger.info("3. Set up scheduled jobs for continuous monitoring")


if __name__ == "__main__":
    asyncio.run(main())
