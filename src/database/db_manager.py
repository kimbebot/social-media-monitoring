"""
Async database operations manager
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime

from .models import Base, Platform, Account, Post, Media, ScraperLog
from config.settings import settings


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
        """Initialize database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
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
    
    async def get_active_platforms(self) -> List[Platform]:
        """Get all active platforms"""
        async with self.get_session() as session:
            result = await session.execute(
                select(Platform).where(Platform.is_active == True)
            )
            return result.scalars().all()
    
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
