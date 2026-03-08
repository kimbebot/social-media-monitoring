"""
Configuration management for Social Media Monitor
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings with validation"""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )
    
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./data/social_monitor.db")
    
    # Security
    encryption_key: str = Field(default="")
    
    # Scraping delays (in seconds)
    min_delay: float = Field(default=2.5, ge=1.0)
    max_delay: float = Field(default=7.0, le=15.0)
    page_load_timeout: int = Field(default=30000)
    scroll_delay_min: float = Field(default=1.5)
    scroll_delay_max: float = Field(default=4.0)
    
    # Browser
    headless: bool = Field(default=True)
    user_data_dir: str = Field(default="./browser_profiles")

    # Execution mode
    run_parallel: bool = Field(default=False)
    
    # Proxy
    use_proxy: bool = Field(default=False)
    proxy_url: Optional[str] = Field(default=None)
    
    # Logging
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./logs/social_monitor.log")
    
    # Rate limiting
    max_concurrent_scrapers: int = Field(default=2, ge=1, le=5)
    scrape_interval_minutes: int = Field(default=180, ge=30)
    
    # Platform toggles
    linkedin_enabled: bool = Field(default=True)
    facebook_enabled: bool = Field(default=True)
    twitter_enabled: bool = Field(default=True)


# Global settings instance
settings = Settings()
