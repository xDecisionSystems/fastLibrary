import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from services.models import BulkUpsertRequest, Paper, PaperUpdate
from services import mongo

router = APIRouter()


@router.post("")
async def create_paper(paper: Paper) -> dict:
    doi = await mongo.upsert_paper(paper)
    return {"doi": doi, "action": "upserted"}


@router.post("/bulk")
async def bulk_upsert(body: BulkUpsertRequest) -> dict:
    if len(body.papers) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 papers per bulk call.")
    return await mongo.bulk_upsert(body.papers)


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
