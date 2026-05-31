import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config.settings import VENUES_DIR
from services.models import VenueRecord
from services.venues import prefill_venue

router = APIRouter(tags=["venues"])

_INVALID_TAG_CHARS = {"/", "\\"}
_MAX_TAG_LENGTH = 64


def _tags_path() -> Path:
    return VENUES_DIR / "_tags.json"


def _normalize_tag(value: str) -> str:
    # Collapse repeated whitespace so tags stay stable for comparison.
    return " ".join(value.strip().split())


def _validate_tag_or_raise(value: str) -> str:
    tag = _normalize_tag(value)
    if not tag:
        raise HTTPException(status_code=422, detail="tag must be a non-empty string")
    if len(tag) > _MAX_TAG_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"tag must be {_MAX_TAG_LENGTH} characters or fewer",
        )
    if any(ch in tag for ch in _INVALID_TAG_CHARS):
        raise HTTPException(
            status_code=422,
            detail="tag cannot contain '/' or '\\'",
        )
    return tag


def _sanitize_tags(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        tag = _normalize_tag(value)
        if not tag:
            continue
        if any(ch in tag for ch in _INVALID_TAG_CHARS):
            continue
        if len(tag) > _MAX_TAG_LENGTH:
            continue
        result.append(tag)
    return sorted(set(result))


def _load_tags() -> list[str]:
    p = _tags_path()
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return _sanitize_tags(raw)
    except Exception:
        return []


def _save_tags(tags: list[str]) -> None:
    p = _tags_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(_sanitize_tags(tags), indent=2), encoding="utf-8")


def _slug(short_name: str) -> str:
    return re.sub(r"\W+", "_", short_name.strip().lower()).strip("_")


def _venue_path(slug: str) -> Path:
    return VENUES_DIR / f"{slug}.json"


def _remove_tag_from_venues(tag: str) -> None:
    VENUES_DIR.mkdir(parents=True, exist_ok=True)
    for venue_file in sorted(VENUES_DIR.glob("*.json")):
        # Skip the dedicated tags registry file.
        if venue_file.name == "_tags.json":
            continue
        try:
            doc = json.loads(venue_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        existing_tags = _sanitize_tags(doc.get("tags", []))
        if tag not in existing_tags:
            continue
        doc["tags"] = [existing for existing in existing_tags if existing != tag]
        venue_file.write_text(json.dumps(doc, indent=2), encoding="utf-8")


@router.get("/prefill")
async def get_prefill(name: str):
    return prefill_venue(name)



@router.post("", status_code=201)
async def create_venue(venue: VenueRecord):
    slug = _slug(venue.short_name)
    if not slug:
        raise HTTPException(status_code=422, detail="short_name produced an empty slug")
    try:
        path = _venue_path(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = venue.model_dump()
        data["tags"] = _sanitize_tags(data.get("tags", []))
        data["slug"] = slug
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"slug": slug, **data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to save venue") from exc


@router.get("")
async def list_venues():
    VENUES_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for f in sorted(VENUES_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "slug": d.get("slug", f.stem),
                "short_name": d.get("short_name", ""),
                "long_name": d.get("long_name", ""),
                "type": d.get("type", ""),
                "publisher": d.get("publisher", ""),
                "due_date_month": d.get("due_date_month", ""),
                "website_url": d.get("website_url", d.get("access_url", "")),
                "proceedings_url": d.get("proceedings_url", ""),
                "open_access": d.get("open_access", False),
                "tags": _sanitize_tags(d.get("tags", [])),
            })
        except Exception:
            continue
    return result


@router.get("/tags")
async def get_tags():
    return _load_tags()


@router.post("/tags", status_code=201)
async def add_tag(body: dict):
    tag = _validate_tag_or_raise(body.get("tag") or "")
    tags = _load_tags()
    if tag not in tags:
        tags.append(tag)
        _save_tags(tags)
    return _load_tags()


@router.delete("/tags/{tag}")
async def delete_tag(tag: str):
    tag = _validate_tag_or_raise(tag)
    tags = _load_tags()
    if tag not in tags:
        raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")
    tags.remove(tag)
    _save_tags(tags)
    _remove_tag_from_venues(tag)
    return _load_tags()


@router.get("/{slug}")
async def get_venue(slug: str):
    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.put("/{slug}")
async def update_venue(slug: str, venue: VenueRecord):
    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    try:
        data = venue.model_dump()
        data["tags"] = _sanitize_tags(data.get("tags", []))
        data["slug"] = slug
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update venue") from exc


@router.delete("/{slug}", status_code=200)
async def delete_venue(slug: str):
    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    path.unlink()
    return {"deleted": slug}
