"""initial schema

Revision ID: 20260211_150000
Revises: 
Create Date: 2026-02-11 15:00:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260211_150000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("base_url", sa.String(length=255)),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_scraped_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id"), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255)),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("session_valid", sa.Boolean(), default=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_ip", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("cookies_data", sa.JSON(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
    )
    op.create_index("idx_platform_username", "accounts", ["platform_id", "username"], unique=True)
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("post_url", sa.Text(), nullable=False),
        sa.Column("author_name", sa.String(length=255)),
        sa.Column("author_username", sa.String(length=255)),
        sa.Column("author_url", sa.Text()),
        sa.Column("author_profile_image", sa.Text()),
        sa.Column("content", sa.Text()),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("scraped_at", sa.DateTime()),
        sa.Column("likes_count", sa.Integer(), default=0),
        sa.Column("comments_count", sa.Integer(), default=0),
        sa.Column("shares_count", sa.Integer(), default=0),
        sa.Column("views_count", sa.Integer(), default=0),
        sa.Column("is_promoted", sa.Boolean(), default=False),
        sa.Column("is_repost", sa.Boolean(), default=False),
        sa.Column("raw_data", sa.JSON(), nullable=True),
    )
    op.create_index("idx_platform_external_id", "posts", ["platform_id", "external_id"], unique=True)
    op.create_index("idx_posted_at", "posts", ["posted_at"], unique=False)
    op.create_index("idx_scraped_at", "posts", ["scraped_at"], unique=False)
    op.create_table(
        "media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("post_id", sa.Integer(), sa.ForeignKey("posts.id"), nullable=False),
        sa.Column("media_type", sa.String(length=20)),
        sa.Column("media_url", sa.Text(), nullable=False),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("duration", sa.Integer()),
        sa.Column("file_size", sa.Integer()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "scraper_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id")),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("log_level", sa.String(length=20)),
        sa.Column("message", sa.Text()),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("posts_scraped", sa.Integer(), default=0),
        sa.Column("new_posts_count", sa.Integer(), default=0),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("idx_log_created_at", "scraper_logs", ["created_at"], unique=False)
    op.create_index("idx_log_level", "scraper_logs", ["log_level"], unique=False)
    op.create_table(
        "monitored_urls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform_id", sa.Integer(), sa.ForeignKey("platforms.id"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_index("idx_monitored_platform_url", "monitored_urls", ["platform_id", "url"], unique=True)
    op.create_index("idx_monitored_active", "monitored_urls", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_monitored_active", table_name="monitored_urls")
    op.drop_index("idx_monitored_platform_url", table_name="monitored_urls")
    op.drop_table("monitored_urls")
    op.drop_index("idx_log_level", table_name="scraper_logs")
    op.drop_index("idx_log_created_at", table_name="scraper_logs")
    op.drop_table("scraper_logs")
    op.drop_table("media")
    op.drop_index("idx_scraped_at", table_name="posts")
    op.drop_index("idx_posted_at", table_name="posts")
    op.drop_index("idx_platform_external_id", table_name="posts")
    op.drop_table("posts")
    op.drop_index("idx_platform_username", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("platforms")
