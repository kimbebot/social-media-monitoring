"""
Async database operations manager
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime

from .models import Base, Platform, Account, Post, Media, ScraperLog, MonitoredUrl
from app.config.settings import settings


class DatabaseManager:
    """Manage all database operations"""
    
    def __init__(self):
        self.engine = create_async_engine(
            settings.database_url,
            echo=False,
            future=True
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def init_db(self):
        """Initialize database connection (tables are managed by Alembic)."""
        from sqlalchemy import text

        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    # Platform operations
    async def get_or_create_platform(self, name: str, base_url: str) -> Platform:
        """Get existing platform or create new one"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Platform).where(Platform.name == name)
            )
            platform = result.scalar_one_or_none()
            
            if not platform:
                platform = Platform(name=name, base_url=base_url)
                session.add(platform)
                await session.commit()
                await session.refresh(platform)
            
            return platform

    async def ensure_default_platforms(self) -> List[Platform]:
        """Seed default platforms if missing."""
        defaults = [
            ("linkedin", "https://www.linkedin.com"),
            ("facebook", "https://www.facebook.com"),
            ("twitter", "https://x.com"),
        ]
        platforms = []
        for name, base_url in defaults:
            platform = await self.get_or_create_platform(name=name, base_url=base_url)
            platforms.append(platform)
        return platforms
    
    async def get_active_platforms(self) -> List[Platform]:
        """Get all active platforms"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Platform).where(Platform.is_active == True)
            )
            return result.scalars().all()

    async def get_platform_by_id(self, platform_id: int) -> Optional[Platform]:
        """Get platform by ID"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Platform).where(Platform.id == platform_id)
            )
            return result.scalar_one_or_none()
    
    # Account operations
    async def create_account(self, platform_id: int, username: str, 
                           email: str, password_encrypted: str) -> Account:
        """Create new account"""
        async with self.get_session() as session:
            account = Account(
                platform_id=platform_id,
                username=username,
                email=email,
                password_encrypted=password_encrypted
            )
            session.add(account)
            await session.commit()
            await session.refresh(account)
            return account
    
    async def get_account(self, platform_id: int, username: str) -> Optional[Account]:
        """Get account by platform and username"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Account).where(
                    and_(
                        Account.platform_id == platform_id,
                        Account.username == username
                    )
                )
            )
            return result.scalar_one_or_none()

    async def get_first_active_account(self, platform_id: int) -> Optional[Account]:
        """Get first active account for a platform"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Account).where(
                    and_(
                        Account.platform_id == platform_id,
                        Account.is_active == True
                    )
                ).limit(1)
            )
            return result.scalar_one_or_none()
    
    async def update_account_session(self, account_id: int, 
                                    cookies_data: dict, user_agent: str):
        """Update account session data"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Account).where(Account.id == account_id)
            )
            account = result.scalar_one_or_none()
            
            if account:
                account.cookies_data = cookies_data
                account.user_agent = user_agent
                account.session_valid = True
                account.last_login_at = datetime.utcnow()
                await session.commit()

    async def set_account_active(self, account_id: int, is_active: bool) -> bool:
        """Activate/deactivate an account"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Account).where(Account.id == account_id)
            )
            account = result.scalar_one_or_none()
            if not account:
                return False
            account.is_active = is_active
            await session.commit()
            return True
    
    # Post operations
    async def create_post(self, post_data: dict) -> Optional[Post]:
        """Create new post if it doesn't exist"""
        async with self.get_session() as session:
            # Check if post already exists
            result = await session.execute(
                select(Post).where(
                    and_(
                        Post.platform_id == post_data['platform_id'],
                        Post.external_id == post_data['external_id']
                    )
                )
            )
            existing_post = result.scalar_one_or_none()
            
            if existing_post:
                return None  # Post already exists
            
            # Create new post
            post = Post(**post_data)
            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post
    
    async def get_latest_post_date(self, platform_id: int) -> Optional[datetime]:
        """Get the date of the most recent post for a platform"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Post.posted_at)
                .where(Post.platform_id == platform_id)
                .order_by(Post.posted_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
    
    async def bulk_create_posts(self, posts_data: List[dict]) -> int:
        """Bulk create posts, skip duplicates"""
        new_count = 0
        async with self.get_session() as session:
            for post_data in posts_data:
                result = await session.execute(
                    select(Post).where(
                        and_(
                            Post.platform_id == post_data['platform_id'],
                            Post.external_id == post_data['external_id']
                        )
                    )
                )
                if result.scalar_one_or_none() is None:
                    post = Post(**post_data)
                    session.add(post)
                    new_count += 1
            
            await session.commit()
        return new_count

    # Monitored URL operations
    async def create_monitored_url(
        self,
        platform_id: int,
        url: str,
        label: Optional[str] = None,
        is_active: bool = True
    ) -> MonitoredUrl:
        """Create a monitored URL"""
        async with self.get_session() as session:
            monitored = MonitoredUrl(
                platform_id=platform_id,
                url=url,
                label=label,
                is_active=is_active
            )
            session.add(monitored)
            await session.commit()
            await session.refresh(monitored)
            return monitored

    async def list_monitored_urls(self) -> List[MonitoredUrl]:
        """List all monitored URLs"""
        async with self.get_session() as session:
            result = await session.execute(select(MonitoredUrl))
            return result.scalars().all()

    async def get_active_monitored_urls(self) -> List[MonitoredUrl]:
        """List active monitored URLs"""
        async with self.get_session() as session:
            result = await session.execute(
                select(MonitoredUrl).where(MonitoredUrl.is_active == True)
            )
            return result.scalars().all()

    async def update_monitored_url(self, monitored_id: int, data: dict) -> Optional[MonitoredUrl]:
        """Update monitored URL"""
        async with self.get_session() as session:
            result = await session.execute(
                select(MonitoredUrl).where(MonitoredUrl.id == monitored_id)
            )
            monitored = result.scalar_one_or_none()
            if not monitored:
                return None
            for key, value in data.items():
                setattr(monitored, key, value)
            await session.commit()
            await session.refresh(monitored)
            return monitored

    async def get_new_posts_for_url(
        self, platform_id: int, url: str, since: Optional[datetime]
    ) -> List[Post]:
        """Get posts for a URL newer than a timestamp."""
        async with self.get_session() as session:
            query = select(Post).where(
                and_(
                    Post.platform_id == platform_id,
                    Post.author_url == url,
                )
            )
            if since:
                query = query.where(Post.scraped_at > since)
            result = await session.execute(query.order_by(Post.scraped_at.asc()))
            return result.scalars().all()

    async def delete_monitored_url(self, monitored_id: int) -> bool:
        """Delete monitored URL"""
        async with self.get_session() as session:
            result = await session.execute(
                select(MonitoredUrl).where(MonitoredUrl.id == monitored_id)
            )
            monitored = result.scalar_one_or_none()
            if not monitored:
                return False
            await session.delete(monitored)
            await session.commit()
            return True
    
    # Media operations
    async def create_media(self, post_id: int, media_data: List[dict]):
        """Create media attachments for a post"""
        async with self.get_session() as session:
            for item in media_data:
                media = Media(post_id=post_id, **item)
                session.add(media)
            await session.commit()
    
    # Logging operations
    async def create_scraper_log(self, log_data: dict) -> ScraperLog:
        """Create scraper log entry"""
        async with self.get_session() as session:
            log = ScraperLog(**log_data)
            session.add(log)
            await session.commit()
            await session.refresh(log)
            return log
    
    async def update_scraper_log(self, log_id: int, update_data: dict):
        """Update scraper log"""
        async with self.get_session() as session:
            result = await session.execute(
                select(ScraperLog).where(ScraperLog.id == log_id)
            )
            log = result.scalar_one_or_none()
            
            if log:
                for key, value in update_data.items():
                    setattr(log, key, value)
                await session.commit()


# Global database instance
db = DatabaseManager()
