from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, hide_input_in_errors=True)

    @field_validator("*")
    @classmethod
    def valid_unicode(cls, value: object) -> object:
        if isinstance(value, str):
            if "\x00" in value:
                raise ValueError("NUL is not supported in text fields")
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError("Invalid Unicode") from None
        return value


class Pair(Schema):
    key: str = Field(max_length=200)
    value: str = Field(max_length=10000)


class HttpRequest(Schema):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    url: str = Field(min_length=1, max_length=8192)
    headers: list[Pair] = Field(default_factory=list, max_length=50)
    variables: list[Pair] = Field(default_factory=list, max_length=50)
    body: str = Field(default="", max_length=524288)
    body_type: Literal["json", "form", "text"] = "json"
    auth_type: Literal["none", "basic", "bearer"] = "none"
    username: str = Field(default="", max_length=255)
    password: str = Field(default="", max_length=10000)
    token: str = Field(default="", max_length=10000)
    timeout: int = Field(default=15, ge=1, le=30)
    allow_private: bool = False
    history_limit: int = Field(default=50, ge=1, le=200)


class HttpResult(Schema):
    status: int | None = None
    elapsed_ms: int = 0
    size_bytes: int = 0
    headers: list[Pair] = Field(default_factory=list)
    body: str = ""
    error: str = ""
    truncated: bool = False
    history_saved: bool = False


class HistorySummary(Schema):
    id: UUID
    method: str
    response_status: int | None
    response_time_ms: int
    response_size_bytes: int
    created_at: datetime


class CollectionInput(Schema):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Collection name is required")
        return value


class CollectionSummary(CollectionInput):
    id: UUID
    request_count: int = 0
    updated_at: datetime


class SavedRequestInput(Schema):
    name: str = Field(min_length=1, max_length=255)
    request: HttpRequest

    @field_validator("name")
    @classmethod
    def nonempty_request_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Request name is required")
        return value


class SavedRequestSummary(Schema):
    id: UUID
    collection_id: UUID
    name: str
    method: str
    updated_at: datetime


class SavedRequestDetail(SavedRequestSummary):
    request: HttpRequest


class CollectionExportRequest(SavedRequestInput):
    pass


class CollectionExportData(CollectionInput):
    requests: list[CollectionExportRequest] = Field(default_factory=list, max_length=100)


class CollectionDocument(Schema):
    format: Literal["qa-portal-http-collection"]
    schema_version: Literal[1]
    exported_at: datetime
    collection: CollectionExportData


FieldType = Literal[
    "full_name",
    "first_name",
    "last_name",
    "email",
    "phone",
    "address",
    "company",
    "uuid",
    "integer",
    "boolean",
    "date",
    "lorem",
    "enum",
]


class DummyField(Schema):
    name: str = Field(min_length=1, max_length=63, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    type: FieldType
    minimum: int = Field(default=0, ge=-1000000000, le=1000000000)
    maximum: int = Field(default=100, ge=-1000000000, le=1000000000)
    start: date = date(2026, 1, 1)
    end: date = date(2026, 12, 31)
    choices: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def ranges(self) -> "DummyField":
        if (self.type == "integer" and self.minimum > self.maximum) or (
            self.type == "date" and self.start > self.end
        ):
            raise ValueError("Invalid range")
        if self.type == "enum" and not self.choices.strip():
            raise ValueError("Enum needs choices")
        return self


class PresetInput(Schema):
    name: str = Field(min_length=1, max_length=255)
    fields: list[DummyField] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_fields(self) -> "PresetInput":
        if not self.name.strip() or len({field.name for field in self.fields}) != len(self.fields):
            raise ValueError("Preset name and unique field names required")
        return self


class PresetOutput(PresetInput):
    id: UUID
