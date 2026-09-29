"""Add optional activity details for manmonth exports."""

import sqlalchemy as sa
from alembic import op

revision = "0008_report_item_manmonth"
down_revision = "0007_report_item_duration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("report_items", sa.Column("obstacle", sa.Text()))
    op.add_column("report_items", sa.Column("next_step", sa.Text()))
    op.add_column("report_items", sa.Column("pic_guidance", sa.Text()))
    op.add_column("report_items", sa.Column("deliverable", sa.Text()))


def downgrade() -> None:
    op.drop_column("report_items", "deliverable")
    op.drop_column("report_items", "pic_guidance")
    op.drop_column("report_items", "next_step")
    op.drop_column("report_items", "obstacle")
