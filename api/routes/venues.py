import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from config.settings import settings
from services.models import VenueRecord
from services.venues import prefill_venue

router = APIRouter(tags=["venues"])


def _slug(short_name: str) -> str:
    return re.sub(r"\W+", "_", short_name.strip().lower()).strip("_")


def _venue_path(slug: str) -> Path:
    return settings.venues_dir / f"{slug}.json"


@router.get("/prefill")
async def get_prefill(name: str):
    return prefill_venue(name)


@router.post("", status_code=201)
async def create_venue(venue: VenueRecord):
    slug = _slug(venue.short_name)
    if not slug:
        raise HTTPException(status_code=422, detail="short_name produced an empty slug")
    path = _venue_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = venue.model_dump()
    data["slug"] = slug
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"slug": slug, **data}


@router.get("")
async def list_venues():
    settings.venues_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for f in sorted(settings.venues_dir.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "slug": d.get("slug", f.stem),
                "short_name": d.get("short_name", ""),
                "long_name": d.get("long_name", ""),
                "type": d.get("type", ""),
                "open_access": d.get("open_access", False),
            })
        except Exception:
            continue
    return result


@router.get("/{slug}")
async def get_venue(slug: str):
    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.delete("/{slug}", status_code=200)
async def delete_venue(slug: str):
    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    path.unlink()
    return {"deleted": slug}
