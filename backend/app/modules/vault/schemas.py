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


class VaultBackupSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        ser_json_bytes="base64",
        val_json_bytes="base64",
    )


class VaultMasterBackup(VaultBackupSchema):
    id: UUID
    pin_hash: str
    kdf_salt: bytes = Field(min_length=16, max_length=16)
    failed_attempts: int
    locked_until: datetime | None
    recovery_code_hash: str | None
    created_at: datetime
    updated_at: datetime


class VaultEntryBackup(VaultBackupSchema):
    id: UUID
    title: str
    username: str | None
    category: VaultCategory
    url: str | None
    value_ciphertext: bytes = Field(min_length=17, max_length=65_552)
    value_nonce: bytes = Field(min_length=12, max_length=12)
    notes_ciphertext: bytes | None = Field(default=None, min_length=16, max_length=65_552)
    notes_nonce: bytes | None = Field(default=None, min_length=12, max_length=12)
    last_accessed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VaultLogBackup(VaultBackupSchema):
    id: UUID
    secret_id: UUID | None
    action: str = Field(min_length=1, max_length=50)
    detail: str | None
    created_at: datetime


class VaultBackup(VaultBackupSchema):
    format: Literal["qa-portal-vault"]
    schema_version: Literal[1]
    master_lock: VaultMasterBackup | None
    entries: list[VaultEntryBackup] = Field(max_length=1000)
    access_logs: list[VaultLogBackup] = Field(max_length=100000)

    @model_validator(mode="after")
    def internally_consistent(self) -> "VaultBackup":
        entry_ids = [entry.id for entry in self.entries]
        log_ids = [log.id for log in self.access_logs]
        if len(entry_ids) != len(set(entry_ids)) or len(log_ids) != len(set(log_ids)):
            raise ValueError("Vault backup IDs must be unique")
        if self.entries and self.master_lock is None:
            raise ValueError("Vault entries require a master lock")
        if any(
            log.secret_id is not None and log.secret_id not in entry_ids for log in self.access_logs
        ):
            raise ValueError("Vault log references an entry outside the backup")
        if any(
            (entry.notes_ciphertext is None) != (entry.notes_nonce is None)
            for entry in self.entries
        ):
            raise ValueError("Vault note ciphertext and nonce must be paired")
        return self


class VaultRestoreResult(BaseModel):
    restored: int
    skipped: int
