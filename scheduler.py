#!/usr/bin/env python3
"""
Scheduled scraper runner
Runs scrapers on a schedule with randomized timing
"""
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
import random

from main import SocialMediaMonitor
from src.database.db_manager import db
from sqlalchemy import select
from src.database.models import Account, Platform
from src.utils.encryption import encryption
from config.settings import settings


class ScheduledMonitor:
    """Scheduled monitoring with smart timing"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.monitor = None
    
    async def initialize(self):
        """Initialize the monitor"""
        self.monitor = SocialMediaMonitor()
        await self.monitor.initialize()
    
    async def scrape_account(self, platform_name: str, account: Account):
        """Scrape a single account"""
        try:
            # Decrypt password
            password = encryption.decrypt(account.password_encrypted)
            
            # Add random delay before starting (1-5 minutes)
            delay_minutes = random.uniform(1, 5)
            logger.info(f"Waiting {delay_minutes:.1f} minutes before scraping {account.username}...")
            await asyncio.sleep(delay_minutes * 60)
            
            # Run scraper
            logger.info(f"Starting scraper for {platform_name} - {account.username}")
            await self.monitor.run_scraper(platform_name, account.username, password)
            
        except Exception as e:
            logger.error(f"Error scraping {account.username}: {str(e)}")
    
    async def scrape_all_platforms(self):
        """Scrape all active platforms and accounts"""
        logger.info("="*60)
        logger.info(f"Starting scheduled scrape at {datetime.now()}")
        logger.info("="*60)
        
        try:
            # Get all active platforms
            platforms = await db.get_active_platforms()
            
            for platform in platforms:
                # Get active accounts for this platform
                async with db.get_session() as session:
                    result = await session.execute(
                        select(Account)
                        .where(Account.platform_id == platform.id)
                        .where(Account.is_active == True)
                    )
                    accounts = result.scalars().all()
                
                if not accounts:
                    logger.warning(f"No active accounts for {platform.name}")
                    continue
                
                logger.info(f"Processing {len(accounts)} accounts for {platform.name}")
                
                # Scrape each account with delay
                for account in accounts:
                    await self.scrape_account(platform.name, account)
                    
                    # Delay between accounts (5-10 minutes)
                    if account != accounts[-1]:  # Not the last account
                        delay = random.uniform(5, 10)
                        logger.info(f"Waiting {delay:.1f} minutes before next account...")
                        await asyncio.sleep(delay * 60)
            
            logger.success("Scheduled scrape completed")
            
        except Exception as e:
            logger.error(f"Error in scheduled scrape: {str(e)}")
    
    def add_jobs(self):
        """Add scheduled jobs"""
        # Random interval between 2.5-3.5 hours
        interval_minutes = random.randint(150, 210)
        
        logger.info(f"Setting up scheduler with ~{interval_minutes/60:.1f} hour intervals")
        
        # Add main scraping job
        self.scheduler.add_job(
            self.scrape_all_platforms,
            IntervalTrigger(minutes=interval_minutes),
            id='main_scraper',
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=600  # 10 minutes
        )
        
        # Reschedule with new random interval after each run
        self.scheduler.add_listener(
            self._on_job_executed,
            event=2  # EVENT_JOB_EXECUTED
        )
    
    def _on_job_executed(self, event):
        """Called after each job execution"""
        # Reschedule with new random interval
        interval_minutes = random.randint(150, 210)
        logger.info(f"Rescheduling next run in ~{interval_minutes/60:.1f} hours")
        
        self.scheduler.reschedule_job(
            'main_scraper',
            trigger=IntervalTrigger(minutes=interval_minutes)
        )
    
    async def start(self):
        """Start the scheduler"""
        await self.initialize()
        self.add_jobs()
        
        logger.success("Scheduler started successfully")
        logger.info("Press Ctrl+C to stop")
        
        self.scheduler.start()
        
        # Run immediately once
        logger.info("Running initial scrape...")
        await self.scrape_all_platforms()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Shutting down scheduler...")
            self.scheduler.shutdown()


async def main():
    """Main entry point"""
    scheduler = ScheduledMonitor()
    await scheduler.start()


if __name__ == "__main__":
    logger.info("Starting Social Media Monitor Scheduler")
    asyncio.run(main())
