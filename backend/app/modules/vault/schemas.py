from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

VaultCategory = Literal["password", "api_key", "token", "command", "note", "other"]
VaultSort = Literal["recent", "alphabetical", "created"]


def validate_master_secret(value: SecretStr) -> SecretStr:
    secret = value.get_secret_value()
    minimum = 6 if secret.isdigit() else 8
    if not minimum <= len(secret) <= 128:
        raise ValueError("Master PIN must be 6+ digits or a passphrase must be 8+ characters")
    return value


class VaultSetup(BaseModel):
    secret: SecretStr
    confirmation: SecretStr
    auto_lock_minutes: int = Field(default=5, ge=1, le=60)

    _valid_secret = field_validator("secret")(validate_master_secret)

    @model_validator(mode="after")
    def matching_secret(self) -> "VaultSetup":
        if self.secret.get_secret_value() != self.confirmation.get_secret_value():
            raise ValueError("Master confirmation does not match")
        return self


class VaultUnlock(BaseModel):
    secret: SecretStr
    auto_lock_minutes: int = Field(default=5, ge=1, le=60)

    _valid_secret = field_validator("secret")(validate_master_secret)


class VaultStatus(BaseModel):
    configured: bool
    unlocked: bool


class VaultUnlockResult(VaultStatus):
    token: str
    auto_lock_minutes: int


class VaultEntryInput(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    username: str = Field(default="", max_length=255)
    category: VaultCategory = "other"
    url: str = Field(default="", max_length=2048)
    value: SecretStr
    notes: SecretStr = SecretStr("")

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title is required")
        return value.strip()

    @field_validator("value")
    @classmethod
    def valid_value(cls, value: SecretStr) -> SecretStr:
        if not 1 <= len(value.get_secret_value()) <= 65_536:
            raise ValueError("Value must contain 1-65536 characters")
        return value

    @field_validator("url")
    @classmethod
    def safe_url(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned and not cleaned.lower().startswith(("http://", "https://")):
            raise ValueError("URL must use HTTP or HTTPS")
        return cleaned


class VaultEntrySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    username: str | None
    category: VaultCategory
    url: str | None
    last_accessed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VaultEntryDetail(BaseModel):
    value: str
    notes: str


class VaultSecretValue(BaseModel):
    value: str
