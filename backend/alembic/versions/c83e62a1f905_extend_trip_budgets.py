"""extend trip categories, travelers and actual spending

Revision ID: c83e62a1f905
Revises: b72d91f4c803
Create Date: 2026-11-04 14:20:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c83e62a1f905"
down_revision: str | Sequence[str] | None = "b72d91f4c803"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("trips") as batch:
        batch.add_column(sa.Column("travelers", sa.Integer(), server_default="1", nullable=False))
        batch.create_check_constraint("ck_trips_travelers_range", "travelers BETWEEN 1 AND 20")
    with op.batch_alter_table("trip_items") as batch:
        batch.add_column(
            sa.Column(
                "category",
                sa.Enum(
                    "transport",
                    "lodging",
                    "food",
                    "activity",
                    "other",
                    name="tripitemcategory",
                    native_enum=False,
                    create_constraint=True,
                    length=10,
                ),
                server_default="activity",
                nullable=False,
            )
        )
        batch.add_column(sa.Column("actual_cost_cents", sa.BigInteger(), nullable=True))
        batch.add_column(sa.Column("ledger_transaction_id", sa.BigInteger(), nullable=True))
        batch.create_check_constraint(
            "ck_trip_items_actual_cost_positive",
            "actual_cost_cents IS NULL OR actual_cost_cents > 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("trip_items") as batch:
        batch.drop_constraint("ck_trip_items_actual_cost_positive", type_="check")
        batch.drop_column("ledger_transaction_id")
        batch.drop_column("actual_cost_cents")
        batch.drop_column("category")
    with op.batch_alter_table("trips") as batch:
        batch.drop_constraint("ck_trips_travelers_range", type_="check")
        batch.drop_column("travelers")
