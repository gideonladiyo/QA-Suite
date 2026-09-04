from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HttpHistory(Base):
    __tablename__ = "http_client_history"
    __table_args__ = (
        CheckConstraint("method IN ('GET','POST','PUT','PATCH','DELETE')", name="ck_http_method"),
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    method: Mapped[str] = mapped_column(String(10))
    request_ciphertext: Mapped[bytes]
    request_nonce: Mapped[bytes]
    response_status: Mapped[int | None]
    response_time_ms: Mapped[int]
    response_size_bytes: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class DummyPreset(Base):
    __tablename__ = "dummy_data_presets"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), unique=True)
    schema_json: Mapped[list[dict[str, object]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HttpCollection(Base):
    __tablename__ = "http_collections"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HttpSavedRequest(Base):
    __tablename__ = "http_saved_requests"
    __table_args__ = (
        CheckConstraint(
            "method IN ('GET','POST','PUT','PATCH','DELETE')", name="ck_http_saved_request_method"
        ),
        UniqueConstraint("collection_id", "name", name="uq_http_saved_request_collection_name"),
    )
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("http_collections.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    method: Mapped[str] = mapped_column(String(10))
    request_ciphertext: Mapped[bytes]
    request_nonce: Mapped[bytes]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
