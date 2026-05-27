from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Paper(BaseModel):
    doi: str
    title: str = ""
    authors: list[str] = []
    publication_year: Optional[int] = None
    source: str = ""
    url: str = ""
    pdf_link: str = ""
    pdf_path: str = ""
    snippet: str = ""
    is_abstract: bool = False
    tags: list[str] = []
    ingested: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
