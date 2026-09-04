"""Store custom template values per activity without changing existing reports."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_activity_template_values"
down_revision = "0003_qa_report_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "report_items",
        sa.Column("template_values", postgresql.JSONB(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("report_items", "template_values")
