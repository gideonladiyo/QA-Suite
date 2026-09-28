"""Add encrypted Vault with master lock and command entries."""

import sqlalchemy as sa
from alembic import op

revision = "0006_vault"
down_revision = "0005_http_collections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vault_master_lock",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pin_hash", sa.Text(), nullable=False),
        sa.Column("kdf_salt", sa.LargeBinary(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("recovery_code_hash", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "vault_secrets",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255)),
        sa.Column("category", sa.String(50), nullable=False, server_default="other"),
        sa.Column("url", sa.Text()),
        sa.Column("value_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("value_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("notes_ciphertext", sa.LargeBinary()),
        sa.Column("notes_nonce", sa.LargeBinary()),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "category IN ('password','api_key','token','command','note','other')",
            name="ck_vault_secret_category",
        ),
    )
    op.create_index("ix_vault_secrets_title", "vault_secrets", ["title"])
    op.create_index("ix_vault_secrets_category", "vault_secrets", ["category"])
    op.create_table(
        "vault_access_log",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "secret_id",
            sa.UUID(),
            sa.ForeignKey("vault_secrets.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_vault_access_log_secret_id", "vault_access_log", ["secret_id"])
    op.create_index("ix_vault_access_log_created_at", "vault_access_log", ["created_at"])
    for table in ("vault_master_lock", "vault_secrets"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in ("vault_secrets", "vault_master_lock"):
        op.execute(f"DROP TRIGGER trg_{table}_updated_at ON {table}")
    op.drop_table("vault_access_log")
    op.drop_table("vault_secrets")
    op.drop_table("vault_master_lock")
