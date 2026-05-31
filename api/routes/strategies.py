import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config.settings import STRATEGIES_DIR, VENUES_DIR
from services.models import Strategy

router = APIRouter(tags=["strategies"])

_MAX_EXTENDS_DEPTH = 10


def _slug(value: str) -> str:
    return re.sub(r"\W+", "_", value.strip().lower()).strip("_")


def _strategy_path(slug: str) -> Path:
    return STRATEGIES_DIR / f"{slug}.json"


def _load_strategy_doc(slug: str) -> dict:
    path = _strategy_path(slug)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _venues_using_strategy(slug: str) -> list[str]:
    VENUES_DIR.mkdir(parents=True, exist_ok=True)
    dependents: list[str] = []
    for venue_file in sorted(VENUES_DIR.glob("*.json")):
        if venue_file.name == "_tags.json":
            continue
        try:
            raw = json.loads(venue_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(raw, dict):
            continue
        if str(raw.get("strategy") or "_default") != slug:
            continue
        dependents.append(str(raw.get("slug") or venue_file.stem))
    return dependents


def _resolve_strategy(slug: str) -> dict:
    """Return a fully merged strategy by walking the extends chain."""
    chain: list[dict] = []
    seen: set[str] = set()
    current = slug
    while current and len(chain) < _MAX_EXTENDS_DEPTH:
        if current in seen:
            break
        seen.add(current)
        doc = _load_strategy_doc(current)
        if not doc:
            break
        chain.append(doc)
        current = doc.get("extends") or ""

    if not chain:
        return {}

    # Merge from oldest ancestor → newest descendant.
    # Steps are merged by id: descendant steps override ancestor steps with same id.
    base = chain[-1]
    merged_steps: dict[str, dict] = {}
    for doc in reversed(chain):
        for step in doc.get("steps", []):
            if isinstance(step, dict) and step.get("id"):
                merged_steps[step["id"]] = step

    leaf = chain[0]
    return {
        "slug": leaf.get("slug", slug),
        "name": leaf.get("name", ""),
        "description": leaf.get("description", ""),
        "extends": leaf.get("extends"),
        "extends_chain": [d.get("slug", "") for d in reversed(chain)][:-1],
        "steps": list(merged_steps.values()),
        "resolved": True,
    }


@router.get("")
async def list_strategies():
    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for f in sorted(STRATEGIES_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            result.append({
                "slug": d.get("slug", f.stem),
                "name": d.get("name", ""),
                "description": d.get("description", ""),
                "extends": d.get("extends"),
                "step_count": len(d.get("steps", [])),
            })
        except Exception:
            continue
    return result


@router.get("/{slug}/resolved")
async def get_resolved_strategy(slug: str):
    resolved = _resolve_strategy(slug)
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Strategy '{slug}' not found")
    return resolved


@router.get("/{slug}")
async def get_strategy(slug: str):
    doc = _load_strategy_doc(slug)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Strategy '{slug}' not found")
    return doc


@router.post("", status_code=201)
async def create_strategy(strategy: Strategy):
    slug = _slug(strategy.slug)
    if not slug:
        raise HTTPException(status_code=422, detail="slug produced an empty value")
    path = _strategy_path(slug)
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Strategy '{slug}' already exists; use PUT to update")
    try:
        STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
        data = strategy.model_dump()
        data["slug"] = slug
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to save strategy") from exc


@router.put("/{slug}")
async def update_strategy(slug: str, strategy: Strategy):
    path = _strategy_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Strategy '{slug}' not found")
    try:
        data = strategy.model_dump()
        data["slug"] = slug
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    except Exception as exc:
        raise HTTPException(status_code=500, detail="failed to update strategy") from exc


@router.delete("/{slug}", status_code=200)
async def delete_strategy(slug: str):
    if slug == "_default":
        raise HTTPException(status_code=400, detail="cannot delete the _default strategy")
    path = _strategy_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Strategy '{slug}' not found")
    in_use_by = _venues_using_strategy(slug)
    if in_use_by:
        joined = ", ".join(sorted(in_use_by))
        raise HTTPException(
            status_code=409,
            detail=f"Strategy '{slug}' is in use by venue(s): {joined}",
        )
    path.unlink()
    return {"deleted": slug}
