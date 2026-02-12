"""add last_exported_at to monitored_urls

Revision ID: 20260211_153000
Revises: 20260211_150000
Create Date: 2026-02-11 15:30:00
"""
from alembic import op
import sqlalchemy as sa


revision = "20260211_153000"
down_revision = "20260211_150000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("monitored_urls", sa.Column("last_exported_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("monitored_urls", "last_exported_at")
