from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import UpdateOne

from config.settings import settings
from services.models import Paper

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("Motor client is not initialized.")
    return _client


def get_collection() -> AsyncIOMotorCollection:
    return get_client()[settings.mongo_db]["papers"]


async def connect() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)
    coll = get_collection()
    await coll.create_index("doi", unique=True)
    await coll.create_index([("title", "text"), ("tags", "text")])
    await coll.create_index([("source", 1), ("publication_year", 1)])


async def disconnect() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def upsert_paper(paper: Paper) -> str:
    coll = get_collection()
    now = datetime.utcnow()
    doc = paper.model_dump(exclude={"created_at", "updated_at"})
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


async def bulk_upsert(papers: list[Paper]) -> dict:
    coll = get_collection()
    now = datetime.utcnow()
    ops = []
    errors = []

    for paper in papers:
        try:
            doc = paper.model_dump(exclude={"created_at", "updated_at"})
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
        except Exception as exc:
            errors.append({"doi": getattr(paper, "doi", "unknown"), "error": str(exc)})

    if not ops:
        return {"upserted": 0, "modified": 0, "errors": errors}

    result = await coll.bulk_write(ops, ordered=False)
    return {
        "upserted": result.upserted_count,
        "modified": result.modified_count,
        "errors": errors,
    }
