"""create user llm configs

Revision ID: a41c0e72b9d6
Revises: 798a3e6a1aa6
Create Date: 2026-11-01 20:50:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

import app.db.types

revision: str = "a41c0e72b9d6"
down_revision: str | Sequence[str] | None = "798a3e6a1aa6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_llm_configs",
        sa.Column(
            "provider",
            sa.Enum(
                "mimo",
                "deepseek",
                name="llmprovider",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("api_key_ciphertext", sa.Text(), nullable=False),
        sa.Column("key_hint", sa.String(length=24), nullable=False),
        sa.Column("last_tested_at", app.db.types.UTCDateTime(timezone=True), nullable=True),
        sa.Column("last_test_success", sa.Boolean(), nullable=True),
        sa.Column("last_test_error", sa.String(length=200), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", app.db.types.UTCDateTime(timezone=True), nullable=False),
        sa.Column("updated_at", app.db.types.UTCDateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_llm_configs_user_provider"),
    )
    op.create_index(
        op.f("ix_user_llm_configs_user_id"), "user_llm_configs", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_llm_configs_user_id"), table_name="user_llm_configs")
    op.drop_table("user_llm_configs")
