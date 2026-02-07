"""
Database models for social media monitoring
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Platform(Base):
    """Social media platforms"""
    __tablename__ = 'platforms'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # linkedin, facebook, twitter
    base_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    accounts = relationship("Account", back_populates="platform", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="platform", cascade="all, delete-orphan")


class Account(Base):
    """User accounts for each platform"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    platform_id = Column(Integer, ForeignKey('platforms.id'), nullable=False)
    username = Column(String(255), nullable=False)
    email = Column(String(255))
    password_encrypted = Column(Text, nullable=False)  # Encrypted password
    is_active = Column(Boolean, default=True)
    session_valid = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata
    cookies_data = Column(JSON, nullable=True)  # Store session cookies
    user_agent = Column(String(500), nullable=True)
    
    # Relationships
    platform = relationship("Platform", back_populates="accounts")
    
    __table_args__ = (
        Index('idx_platform_username', 'platform_id', 'username', unique=True),
    )


class Post(Base):
    """Scraped social media posts"""
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    platform_id = Column(Integer, ForeignKey('platforms.id'), nullable=False)
    
    # Post identifiers
    external_id = Column(String(255), nullable=False)  # Platform's post ID
    post_url = Column(Text, nullable=False)
    
    # Author information
    author_name = Column(String(255))
    author_username = Column(String(255))
    author_url = Column(Text)
    author_profile_image = Column(Text)
    
    # Content
    content = Column(Text)
    content_html = Column(Text, nullable=True)
    
    # Metadata
    posted_at = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # Engagement metrics
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    
    # Flags
    is_promoted = Column(Boolean, default=False)
    is_repost = Column(Boolean, default=False)
    
    # Raw data
    raw_data = Column(JSON, nullable=True)  # Store complete scraped data
    
    # Relationships
    platform = relationship("Platform", back_populates="posts")
    media = relationship("Media", back_populates="post", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_platform_external_id', 'platform_id', 'external_id', unique=True),
        Index('idx_posted_at', 'posted_at'),
        Index('idx_scraped_at', 'scraped_at'),
    )


class Media(Base):
    """Media attachments (images, videos) for posts"""
    __tablename__ = 'media'
    
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    
    media_type = Column(String(20))  # image, video, gif, document
    media_url = Column(Text, nullable=False)
    thumbnail_url = Column(Text)
    
    # Metadata
    width = Column(Integer)
    height = Column(Integer)
    duration = Column(Integer)  # For videos (in seconds)
    file_size = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    post = relationship("Post", back_populates="media")


class ScraperLog(Base):
    """Log scraping activities and errors"""
    __tablename__ = 'scraper_logs'
    
    id = Column(Integer, primary_key=True)
    platform_id = Column(Integer, ForeignKey('platforms.id'))
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    
    log_level = Column(String(20))  # INFO, WARNING, ERROR
    message = Column(Text)
    error_details = Column(Text, nullable=True)
    
    posts_scraped = Column(Integer, default=0)
    new_posts_count = Column(Integer, default=0)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_log_created_at', 'created_at'),
        Index('idx_log_level', 'log_level'),
    )
