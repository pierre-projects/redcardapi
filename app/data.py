"""Translations dataset: strict schema, loaded and validated once at startup.

The file (data/Translations_with_sources.json) has one shape:
    {version, languages: {code: Language}, back: {statements, footer}, metadata}
Anything else is a startup error, so bad data never reaches a request.
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class Bullet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    text: str = Field(min_length=1)


class Front(BaseModel):
    model_config = ConfigDict(extra="ignore")
    header: str = Field(min_length=1)
    bullets: list[Bullet] = Field(min_length=1)


class Source(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str
    origin: str | None = None
    url: str | None = None
    # False when the text could not be checked against clean source artwork;
    # review_note says why and what a native speaker should check.
    verified: bool = False
    review_note: str | None = None


class Language(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    # Code as written in the data (e.g. "zh-CN"); used in filenames.
    display_code: str = Field(alias="code")
    name: str = Field(min_length=1)
    native: str = Field(min_length=1)
    rtl: bool = False
    front: Front
    source: Source

    @property
    def code(self) -> str:
        """Canonical lowercase code used in URLs and lookups."""
        return self.display_code.lower()

    @property
    def official(self) -> bool:
        return self.source.type == "official"


class Back(BaseModel):
    """English text for the officer, identical on every card."""
    statements: list[Bullet] = Field(min_length=1)
    footer: str = ""

    @property
    def paragraphs(self) -> list[str]:
        return [s.text for s in self.statements] + ([self.footer] if self.footer else [])


class Dataset(BaseModel):
    version: str
    languages: dict[str, Language] = Field(min_length=1)
    back: Back

    @field_validator("languages")
    @classmethod
    def keys_match_codes(cls, languages: dict[str, Language]) -> dict[str, Language]:
        for key, language in languages.items():
            if key.lower() != language.code:
                raise ValueError(f"key {key!r} does not match code {language.display_code!r}")
        return languages


class DatasetError(RuntimeError):
    pass


class TranslationStore:
    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self._by_code = {lang.code: lang for lang in dataset.languages.values()}

    @classmethod
    def load(cls, path: Path) -> "TranslationStore":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
            return cls(Dataset.model_validate(raw))
        except FileNotFoundError as exc:
            raise DatasetError(f"Translations file not found: {path}") from exc
        except (json.JSONDecodeError, ValidationError) as exc:
            raise DatasetError(f"Invalid translations file {path}:\n{exc}") from exc

    @property
    def back(self) -> Back:
        return self.dataset.back

    def languages(self) -> list[Language]:
        return list(self._by_code.values())

    def get(self, code: str) -> Language | None:
        return self._by_code.get((code or "").strip().lower())
