from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from config.settings import settings
from services.models import Paper

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("Motor client is not initialized.")
    return _client


def get_collection() -> AsyncIOMotorCollection:
    return get_client()[settings.mongo_db]["papers"]


def get_search_cache_collection() -> AsyncIOMotorCollection:
    return get_client()[settings.mongo_db]["paper_search_cache"]


async def connect() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)
    coll = get_collection()
    await coll.create_index("doi", unique=True)
    await coll.create_index([("title", "text"), ("tags", "text")])
    await coll.create_index([("source", 1), ("publication_year", 1)])
    cache_coll = get_search_cache_collection()
    await cache_coll.create_index([("slug", 1), ("year", 1)], unique=True)


async def disconnect() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def _paper_update_fields(paper: Paper, overwrite_missing_fields: bool) -> dict:
    if overwrite_missing_fields:
        return paper.model_dump(exclude={"doi", "created_at", "updated_at"})
    return paper.model_dump(
        exclude={"doi", "created_at", "updated_at"},
        exclude_unset=True,
    )


def _normalize_bulk_papers(papers: list[Paper], overwrite_duplicate_doi: bool) -> list[Paper]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for paper in papers:
        if paper.doi in seen:
            duplicates.add(paper.doi)
        seen.add(paper.doi)

    if not duplicates:
        return papers

    if not overwrite_duplicate_doi:
        duplicate_list = ", ".join(sorted(duplicates))
        raise ValueError(
            "Duplicate DOI values found in bulk payload. "
            "Set overwrite_duplicate_doi=true to keep the last record per DOI. "
            f"Duplicate DOI(s): {duplicate_list}"
        )

    deduped: dict[str, Paper] = {}
    for paper in papers:
        deduped[paper.doi] = paper
    return list(deduped.values())


async def upsert_paper(paper: Paper, overwrite_missing_fields: bool = False) -> str:
    coll = get_collection()
    now = datetime.utcnow()
    doc = _paper_update_fields(paper, overwrite_missing_fields)
    await coll.update_one(
        {"doi": paper.doi},
        {
            "$set": {**doc, "updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return paper.doi


async def get_paper(doi: str) -> dict | None:
    coll = get_collection()
    doc = await coll.find_one({"doi": doi}, {"_id": 0})
    return doc


async def list_papers(filters: dict, skip: int, limit: int) -> list[dict]:
    coll = get_collection()
    cursor = coll.find(filters, {"_id": 0}).skip(skip).limit(limit)
    return await cursor.to_list(length=limit)


async def count_papers(filters: dict) -> int:
    coll = get_collection()
    return await coll.count_documents(filters)


async def delete_paper(doi: str) -> bool:
    coll = get_collection()
    result = await coll.delete_one({"doi": doi})
    return result.deleted_count > 0


async def upsert_search_cache(slug: str, year: int, papers: list[dict]) -> None:
    coll = get_search_cache_collection()
    now = datetime.utcnow()
    await coll.update_one(
        {"slug": slug, "year": year},
        {
            "$set": {
                "papers": papers,
                "total": len(papers),
                "searched_at": now,
            },
            "$setOnInsert": {"slug": slug, "year": year},
        },
        upsert=True,
    )


async def get_search_cache(slug: str, year: int) -> dict | None:
    coll = get_search_cache_collection()
    return await coll.find_one({"slug": slug, "year": year}, {"_id": 0})


async def get_search_cache_counts(slug: str, years: list[int]) -> dict[int, int]:
    """Return {year: total} for all cached searches matching slug and given years."""
    coll = get_search_cache_collection()
    cursor = coll.find(
        {"slug": slug, "year": {"$in": years}},
        {"_id": 0, "year": 1, "total": 1},
    )
    return {doc["year"]: doc["total"] async for doc in cursor}


async def delete_all_papers() -> int:
    coll = get_collection()
    result = await coll.delete_many({})
    return result.deleted_count


async def clear_search_cache() -> int:
    coll = get_search_cache_collection()
    result = await coll.delete_many({})
    return result.deleted_count


async def bulk_upsert(
    papers: list[Paper],
    overwrite_missing_fields: bool = False,
    overwrite_duplicate_doi: bool = False,
) -> dict:
    coll = get_collection()
    now = datetime.utcnow()
    ops = []
    op_dois = []
    errors = []
    normalized_papers = _normalize_bulk_papers(papers, overwrite_duplicate_doi)

    for paper in normalized_papers:
        try:
            doc = _paper_update_fields(paper, overwrite_missing_fields)
            ops.append(
                UpdateOne(
                    {"doi": paper.doi},
                    {
                        "$set": {**doc, "updated_at": now},
                        "$setOnInsert": {"created_at": now},
                    },
                    upsert=True,
                )
            )
            op_dois.append(paper.doi)
        except Exception as exc:
            errors.append({"doi": getattr(paper, "doi", "unknown"), "error": str(exc)})

    if not ops:
        return {"upserted": 0, "modified": 0, "errors": errors}

    try:
        result = await coll.bulk_write(ops, ordered=False)
    except BulkWriteError as exc:
        details = exc.details or {}
        write_errors = details.get("writeErrors", [])
        for err in write_errors:
            idx = err.get("index")
            doi = "unknown"
            if isinstance(idx, int) and 0 <= idx < len(op_dois):
                doi = op_dois[idx]
            errors.append({"doi": doi, "error": err.get("errmsg", "bulk write error")})
        return {
            "upserted": details.get("nUpserted", 0),
            "modified": details.get("nModified", 0),
            "errors": errors,
        }

    return {
        "upserted": result.upserted_count,
        "modified": result.modified_count,
        "errors": errors,
    }
