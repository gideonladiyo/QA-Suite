"""Add customizable QA report templates."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_qa_report_templates"
down_revision = "0002_micro_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_templates",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.func.gen_random_uuid()),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("name", name="uq_report_templates_name"),
    )
    op.add_column("daily_reports", sa.Column("template_id", sa.UUID()))
    op.add_column("daily_reports", sa.Column("template_name", sa.String(100)))
    op.add_column("daily_reports", sa.Column("template_body", sa.Text()))
    op.add_column(
        "daily_reports",
        sa.Column("template_values", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_daily_reports_template_id", "daily_reports", ["template_id"])
    op.create_foreign_key(
        "fk_daily_reports_template_id",
        "daily_reports",
        "report_templates",
        ["template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        "CREATE TRIGGER trg_report_templates_updated_at BEFORE UPDATE ON report_templates "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    op.drop_column("daily_reports", "template_values")
    op.drop_constraint("fk_daily_reports_template_id", "daily_reports", type_="foreignkey")
    op.drop_index("ix_daily_reports_template_id", table_name="daily_reports")
    op.drop_column("daily_reports", "template_body")
    op.drop_column("daily_reports", "template_name")
    op.drop_column("daily_reports", "template_id")
    op.execute("DROP TRIGGER trg_report_templates_updated_at ON report_templates")
    op.drop_table("report_templates")
