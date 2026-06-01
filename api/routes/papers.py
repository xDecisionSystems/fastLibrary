import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from config.settings import PDF_DIR, settings
from services.models import BulkUpsertRequest, Paper, PaperUpdate, UpsertRequest
from services import mongo

router = APIRouter()

_PDF_MAGIC = b"%PDF"
_MAX_PDF_BYTES = 200 * 1024 * 1024  # 200 MB
_UPLOAD_CHUNK_BYTES = 1024 * 1024   # 1 MB


def _slugify(text: str, max_words: int | None = None) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    words = text.split()
    if max_words:
        words = words[:max_words]
    return "_".join(words)


def _build_filename(doi: str, record: dict) -> str:
    """
    Build a human-readable PDF filename:
        {venue}_{year}__{title_slug}__{first_author_lastname}.pdf

    Falls back gracefully when fields are missing.
    """
    parts: list[str] = []

    venue = _slugify(record.get("venue", "")).strip("_")
    year = record.get("publication_year")
    if venue and year:
        parts.append(f"{venue}_{year}")
    elif venue:
        parts.append(venue)
    elif year:
        parts.append(str(year))

    title_slug = record.get("title_slug", "").strip()
    if not title_slug:
        title_slug = _slugify(record.get("title", ""), max_words=5).strip("_")
    if title_slug:
        parts.append(title_slug)

    authors = record.get("authors", [])
    if authors:
        last_name = authors[0].strip().split()[-1].lower()
        last_name = re.sub(r"[^\w]", "", last_name)
        if last_name:
            parts.append(last_name)

    if parts:
        return "__".join(parts) + ".pdf"

    # Final fallback: sanitized DOI
    return re.sub(r"[^\w\-]", "_", doi) + ".pdf"


# ── Fixed-path routes must be registered before /{doi:path} catch-alls ────────

@router.post("")
async def create_paper(body: UpsertRequest) -> dict:
    doi = await mongo.upsert_paper(body.paper, overwrite_missing_fields=body.overwrite_missing_fields)
    return {"doi": doi, "action": "upserted"}


@router.post("/bulk")
async def bulk_upsert(body: BulkUpsertRequest) -> dict:
    if len(body.papers) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 papers per bulk call.")
    try:
        return await mongo.bulk_upsert(
            body.papers,
            overwrite_missing_fields=body.overwrite_missing_fields,
            overwrite_duplicate_doi=body.overwrite_duplicate_doi,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
async def list_papers(
    title: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    year_low: Optional[int] = Query(None),
    year_high: Optional[int] = Query(None),
    ingested: Optional[bool] = Query(None),
    tags: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    filters: dict = {}

    if title:
        filters["$text"] = {"$search": title}

    if source:
        filters["source"] = source

    if year_low is not None or year_high is not None:
        year_filter: dict = {}
        if year_low is not None:
            year_filter["$gte"] = year_low
        if year_high is not None:
            year_filter["$lte"] = year_high
        filters["publication_year"] = year_filter

    if ingested is not None:
        filters["ingested"] = ingested

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            filters["tags"] = {"$all": tag_list}

    total = await mongo.count_papers(filters)
    results = await mongo.list_papers(filters, skip=skip, limit=limit)

    for doc in results:
        for key in ("created_at", "updated_at"):
            if isinstance(doc.get(key), datetime):
                doc[key] = doc[key].isoformat()

    return {"total": total, "skip": skip, "limit": limit, "results": results}


# ── Per-DOI routes ─────────────────────────────────────────────────────────────

@router.post("/{doi:path}/pdf")
async def upload_pdf(doi: str, file: UploadFile = File(...)) -> dict:
    existing = await mongo.get_paper(doi)
    if existing is None:
        raise HTTPException(status_code=404, detail="Paper not found. Upload metadata first.")

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    filename = _build_filename(doi, existing)
    dest = PDF_DIR / filename
    tmp_dest = PDF_DIR / f".{filename}.{uuid4().hex}.uploading"

    total_bytes = 0
    first_chunk = True
    try:
        with tmp_dest.open("wb") as fh:
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                if first_chunk and not chunk.startswith(_PDF_MAGIC):
                    raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF.")
                first_chunk = False
                total_bytes += len(chunk)
                if total_bytes > _MAX_PDF_BYTES:
                    raise HTTPException(status_code=413, detail="File exceeds 200 MB limit.")
                fh.write(chunk)
    except Exception:
        if tmp_dest.exists():
            tmp_dest.unlink()
        raise
    finally:
        await file.close()

    if total_bytes == 0:
        if tmp_dest.exists():
            tmp_dest.unlink()
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    tmp_dest.replace(dest)

    coll = mongo.get_collection()
    await coll.update_one(
        {"doi": doi},
        {"$set": {"pdf_path": str(dest), "updated_at": datetime.utcnow()}},
    )

    return {"doi": doi, "pdf_path": str(dest), "size_bytes": total_bytes}


@router.get("/{doi:path}/pdf")
async def serve_pdf(doi: str, download: bool = Query(False)) -> FileResponse:
    doc = await mongo.get_paper(doi)
    if doc is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    pdf_path = str(doc.get("pdf_path") or "").strip()
    if not pdf_path:
        raise HTTPException(status_code=404, detail="No PDF stored for this paper.")
    path = Path(pdf_path).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    base_dir = PDF_DIR.resolve()
    try:
        path.relative_to(base_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Stored PDF path is outside server PDF directory.") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on server.")
    filename = path.name
    disposition = "attachment" if download else "inline"
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


@router.get("/{doi:path}")
async def get_paper(doi: str) -> dict:
    doc = await mongo.get_paper(doi)
    if doc is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    for key in ("created_at", "updated_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()
    return doc


@router.patch("/{doi:path}")
async def update_paper(doi: str, body: PaperUpdate) -> dict:
    existing = await mongo.get_paper(doi)
    if existing is None:
        raise HTTPException(status_code=404, detail="Paper not found.")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    updates["updated_at"] = datetime.utcnow()
    coll = mongo.get_collection()
    await coll.update_one({"doi": doi}, {"$set": updates})

    doc = await mongo.get_paper(doi)
    for key in ("created_at", "updated_at"):
        if isinstance(doc.get(key), datetime):
            doc[key] = doc[key].isoformat()
    return doc


@router.delete("/{doi:path}")
async def delete_paper(doi: str) -> dict:
    deleted = await mongo.delete_paper(doi)
    if not deleted:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return {"deleted": True}
