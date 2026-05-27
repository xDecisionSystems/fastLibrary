from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Paper(BaseModel):
    doi: str = Field(min_length=1)
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    publication_year: Optional[int] = None
    source: str = ""
    url: str = ""
    pdf_link: str = ""
    pdf_path: str = ""
    snippet: str = ""
    is_abstract: bool = False
    tags: list[str] = Field(default_factory=list)
    ingested: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("doi must be a non-empty string.")
        return normalized


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    publication_year: Optional[int] = None
    source: Optional[str] = None
    url: Optional[str] = None
    pdf_link: Optional[str] = None
    pdf_path: Optional[str] = None
    snippet: Optional[str] = None
    is_abstract: Optional[bool] = None
    tags: Optional[list[str]] = None
    ingested: Optional[bool] = None


class BulkUpsertRequest(BaseModel):
    papers: list[Paper]
    overwrite_missing_fields: bool = False
    overwrite_duplicate_doi: bool = False
