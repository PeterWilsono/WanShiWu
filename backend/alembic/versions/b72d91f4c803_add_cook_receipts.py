"""add idempotent cook receipts

Revision ID: b72d91f4c803
Revises: a41c0e72b9d6
Create Date: 2026-11-04 12:40:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

import app.db.types
from alembic import op

revision: str = "b72d91f4c803"
down_revision: str | Sequence[str] | None = "a41c0e72b9d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cook_receipts",
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", app.db.types.UTCDateTime(timezone=True), nullable=False),
        sa.Column("updated_at", app.db.types.UTCDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "request_id", name="uq_cook_receipts_user_request"),
    )
    op.create_index(op.f("ix_cook_receipts_user_id"), "cook_receipts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cook_receipts_user_id"), table_name="cook_receipts")
    op.drop_table("cook_receipts")
