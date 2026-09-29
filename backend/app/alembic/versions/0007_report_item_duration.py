"""Add optional activity duration for manmonth exports."""

import sqlalchemy as sa
from alembic import op

revision = "0007_report_item_duration"
down_revision = "0006_vault"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_items", sa.Column("duration_hours", sa.Float()))


def downgrade() -> None:
    op.drop_column("report_items", "duration_hours")
