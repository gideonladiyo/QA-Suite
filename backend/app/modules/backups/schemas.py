from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HexColor = Annotated[str, Field(pattern=r"^#[0-9a-f]{6}$")]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ColorPalette(Schema):
    ink: HexColor
    violet: HexColor
    mauve: HexColor
    blush: HexColor


class SavedPalette(Schema):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=60)
    colors: ColorPalette


class ThemeBackup(Schema):
    theme: Literal["light", "dark", "system"] = "light"
    color_palette: ColorPalette | None = None
    saved_palettes: list[SavedPalette] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def unique_saved_palettes(self) -> "ThemeBackup":
        ids = [palette.id for palette in self.saved_palettes]
        names = [palette.name.casefold() for palette in self.saved_palettes]
        if len(ids) != len(set(ids)) or len(names) != len(set(names)):
            raise ValueError("Saved palette IDs and names must be unique")
        return self


class BackupManifest(Schema):
    format: Literal["qa-portal-backup"]
    schema_version: Literal[1, 2]
    exported_at: datetime


class ImportPreview(Schema):
    exported_at: datetime
    reports: int
    templates: int
    vault_entries: int
    has_theme: bool
    has_existing_data: bool
    vault_mergeable: bool
    existing_reports: int = Field(ge=0)
    existing_templates: int = Field(ge=0)
    existing_vault_entries: int = Field(ge=0)
    new_reports: int = Field(ge=0)
    new_templates: int = Field(ge=0)
    new_vault_entries: int = Field(ge=0)


class ImportResult(Schema):
    mode: Literal["missing", "overwrite"]
    reports_restored: int
    reports_skipped: int
    vault_restored: int
    vault_skipped: int
    theme: ThemeBackup
