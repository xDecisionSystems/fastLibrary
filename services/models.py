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
    venue: str = ""
    snippet: str = ""
    is_abstract: bool = False
    tags: list[str] = Field(default_factory=list)
    title_slug: str = ""
    ingested: bool = False
    doi_synthetic: bool = False
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
    venue: Optional[str] = None
    snippet: Optional[str] = None
    is_abstract: Optional[bool] = None
    tags: Optional[list[str]] = None
    title_slug: Optional[str] = None
    ingested: Optional[bool] = None
    doi_synthetic: Optional[bool] = None


class UpsertRequest(BaseModel):
    paper: Paper
    overwrite_missing_fields: bool = False


class BulkUpsertRequest(BaseModel):
    papers: list[Paper]
    overwrite_missing_fields: bool = False
    overwrite_duplicate_doi: bool = False


class DownloadSource(BaseModel):
    name: str = ""
    url: str = ""
    notes: str = ""


_MONTH_NAMES = {
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
}


class StrategyStep(BaseModel):
    id: str = Field(min_length=1)
    name: str = ""
    type: str = ""
    description: str = ""
    config: dict = Field(default_factory=dict)


class Strategy(BaseModel):
    slug: str = Field(min_length=1)
    name: str = ""
    description: str = ""
    extends: Optional[str] = None
    steps: list[StrategyStep] = Field(default_factory=list)


class VenueRecord(BaseModel):
    short_name: str = Field(min_length=1)
    long_name: str = ""
    type: str = ""
    publisher: str = ""
    due_date_month: str = ""
    website_url: str = ""
    proceedings_url: str = ""
    open_access: bool = False
    tags: list[str] = Field(default_factory=list)
    strategy: str = ""
    notes: str = ""
    download_sources: list[DownloadSource] = Field(default_factory=list)

    @field_validator("due_date_month")
    @classmethod
    def validate_due_date_month(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            return ""
        titled = normalized.title()
        if titled not in _MONTH_NAMES:
            raise ValueError("due_date_month must be a calendar month name.")
        return titled
