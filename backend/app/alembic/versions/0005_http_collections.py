"""Add encrypted HTTP client collections and saved requests."""

import sqlalchemy as sa
from alembic import op

revision = "0005_http_collections"
down_revision = "0004_activity_template_values"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "http_collections",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "http_saved_requests",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "collection_id",
            sa.UUID(),
            sa.ForeignKey("http_collections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("request_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("request_nonce", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "method IN ('GET','POST','PUT','PATCH','DELETE')",
            name="ck_http_saved_request_method",
        ),
        sa.UniqueConstraint("collection_id", "name", name="uq_http_saved_request_collection_name"),
    )
    op.create_index(
        "ix_http_saved_requests_collection_id", "http_saved_requests", ["collection_id"]
    )
    for table in ("http_collections", "http_saved_requests"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in ("http_saved_requests", "http_collections"):
        op.execute(f"DROP TRIGGER trg_{table}_updated_at ON {table}")
    op.drop_table("http_saved_requests")
    op.drop_table("http_collections")
