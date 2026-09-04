"""Encrypted HTTP history and dummy schema presets; QA data is unchanged."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_micro_tools"
down_revision = "0001_auth_qa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "http_client_history",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("request_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("request_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("response_status", sa.Integer()),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.Column("response_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "method IN ('GET','POST','PUT','PATCH','DELETE')", name="ck_http_method"
        ),
    )
    op.create_index("ix_http_client_history_created_at", "http_client_history", ["created_at"])
    op.create_table(
        "dummy_data_presets",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("schema_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("dummy_data_presets")
    op.drop_table("http_client_history")
