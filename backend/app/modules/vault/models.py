from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VaultMasterLock(Base):
    __tablename__ = "vault_master_lock"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    pin_hash: Mapped[str] = mapped_column(Text)
    kdf_salt: Mapped[bytes] = mapped_column(LargeBinary)
    failed_attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recovery_code_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VaultSecret(Base):
    __tablename__ = "vault_secrets"
    __table_args__ = (
        CheckConstraint(
            "category IN ('password','api_key','token','command','note','other')",
            name="ck_vault_secret_category",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    title: Mapped[str] = mapped_column(String(255), index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(50), default="other", server_default="other")
    url: Mapped[str | None] = mapped_column(Text)
    value_ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    value_nonce: Mapped[bytes] = mapped_column(LargeBinary)
    notes_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    notes_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VaultAccessLog(Base):
    __tablename__ = "vault_access_log"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    secret_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("vault_secrets.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(50))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
