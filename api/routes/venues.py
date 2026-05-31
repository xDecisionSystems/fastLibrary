import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from fastapi import APIRouter, HTTPException, Query

from config.settings import STRATEGIES_DIR, VENUES_DIR, settings
from services import mongo
from services.models import Paper, VenueRecord
from services.venues import prefill_venue

router = APIRouter(tags=["venues"])

_INVALID_TAG_CHARS = {"/", "\\"}
_MAX_TAG_LENGTH = 64
_DOWNLOAD_YEAR_MIN = 1900
_INTERNAL_VENUE_FIELDS = ("paper_downloads",)
_MAX_EXTENDS_DEPTH = 10


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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_year(value: object) -> int | None:
    text = str(value or "").strip()
    if not text.isdigit():
        return None
    year = int(text)
    current_year = datetime.now(timezone.utc).year
    if year < _DOWNLOAD_YEAR_MIN or year > (current_year + 1):
        return None
    return year


def _load_venue_doc(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def _normalize_download_stats(data: object) -> dict[str, dict]:
    if not isinstance(data, dict):
        return {}
    normalized: dict[str, dict] = {}
    for year_key, payload in data.items():
        year = _parse_year(year_key)
        if year is None:
            continue
        entry = payload if isinstance(payload, dict) else {}
        downloaded = entry.get("downloaded_papers", 0)
        if not isinstance(downloaded, int) or downloaded < 0:
            downloaded = 0
        last_attempted_at = str(entry.get("last_attempted_at") or "").strip()
        last_status = str(entry.get("last_status") or "").strip().lower()
        if last_status not in {"success", "error"}:
            last_status = ""
        last_error = str(entry.get("last_error") or "").strip()
        normalized[str(year)] = {
            "downloaded_papers": downloaded,
            "last_attempted_at": last_attempted_at,
            "last_status": last_status,
            "last_error": last_error,
        }
    return normalized


def _conference_years(doc: dict) -> list[int]:
    years: set[int] = set()
    for source in doc.get("download_sources", []):
        if not isinstance(source, dict):
            continue
        year = _parse_year(source.get("name"))
        if year is not None:
            years.add(year)
    for year_key in _normalize_download_stats(doc.get("paper_downloads", {})).keys():
        year = _parse_year(year_key)
        if year is not None:
            years.add(year)
    return sorted(years, reverse=True)


def _build_searcher_payload(venue_doc: dict, year: int) -> dict:
    sources = []
    for source in venue_doc.get("download_sources", []):
        if not isinstance(source, dict):
            continue
        sources.append(
            {
                "name": str(source.get("name") or "").strip(),
                "url": str(source.get("url") or "").strip(),
                "notes": str(source.get("notes") or "").strip(),
            }
        )
    return {
        "year": year,
        "conference": {
            "slug": str(venue_doc.get("slug") or "").strip(),
            "short_name": str(venue_doc.get("short_name") or "").strip(),
            "long_name": str(venue_doc.get("long_name") or "").strip(),
            "publisher": str(venue_doc.get("publisher") or "").strip(),
            "website_url": str(venue_doc.get("website_url") or "").strip(),
            "proceedings_url": str(venue_doc.get("proceedings_url") or "").strip(),
            "download_sources": sources,
        },
    }


def _strategy_path(slug: str) -> Path:
    return STRATEGIES_DIR / f"{slug}.json"


def _load_strategy_doc(slug: str) -> dict:
    path = _strategy_path(slug)
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _resolve_strategy(slug: str) -> dict:
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
        current = str(doc.get("extends") or "").strip()

    if not chain:
        return {}

    merged_steps: dict[str, dict] = {}
    for doc in reversed(chain):
        steps = doc.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, dict) and step.get("id"):
                merged_steps[str(step["id"])] = step

    leaf = chain[0]
    return {
        "slug": leaf.get("slug", slug),
        "name": leaf.get("name", ""),
        "description": leaf.get("description", ""),
        "extends": leaf.get("extends"),
        "steps": list(merged_steps.values()),
    }


def _default_strategy_for_slug(slug: str) -> str:
    """Return slug if a matching strategy file exists, otherwise empty string."""
    if slug and _strategy_path(slug).exists():
        return slug
    return ""


def _find_download_source_for_year(venue_doc: dict, year: int) -> dict:
    for source in venue_doc.get("download_sources", []):
        if not isinstance(source, dict):
            continue
        source_year = _parse_year(source.get("name"))
        if source_year == year:
            return source
    return {}


def _lookup_template_value(token: str, payload: dict, venue_doc: dict, year: int) -> object:
    if token == "year":
        return year
    if token == "conference":
        return payload.get("conference", {})
    if token.startswith("conference."):
        current: object = payload.get("conference", {})
        for part in token.removeprefix("conference.").split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = None
            if current is None:
                raise RuntimeError(f"strategy placeholder '{token}' could not be resolved")
        return current

    source_match = re.fullmatch(r"download_sources\[year\]\.([a-zA-Z_][a-zA-Z0-9_]*)", token)
    if source_match:
        source = _find_download_source_for_year(venue_doc, year)
        key = source_match.group(1)
        value = source.get(key)
        if value is None or str(value).strip() == "":
            raise RuntimeError(
                f"strategy placeholder '{token}' could not be resolved for year {year}"
            )
        return value

    raise RuntimeError(f"unsupported strategy placeholder '{token}'")


def _resolve_template(value: object, payload: dict, venue_doc: dict, year: int) -> object:
    if isinstance(value, dict):
        return {
            str(key): _resolve_template(item, payload, venue_doc, year)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_resolve_template(item, payload, venue_doc, year) for item in value]
    if not isinstance(value, str):
        return value

    exact_match = re.fullmatch(r"\{([^{}]+)\}", value)
    if exact_match:
        return _lookup_template_value(exact_match.group(1), payload, venue_doc, year)

    def _sub(match: re.Match[str]) -> str:
        token = match.group(1)
        return str(_lookup_template_value(token, payload, venue_doc, year))

    return re.sub(r"\{([^{}]+)\}", _sub, value)


def _build_searcher_url(base_url: str, endpoint: str) -> str:
    base = base_url.strip()
    if not base:
        return ""
    tail = endpoint.strip()
    if not tail:
        return base
    if re.match(r"^https?://", tail, flags=re.IGNORECASE):
        return tail
    normalized_tail = tail.lstrip("/")
    if base.rstrip("/").endswith(normalized_tail):
        return base.rstrip("/")
    return f"{base.rstrip('/')}/{normalized_tail}"


def _build_searcher_request(venue_doc: dict, year: int) -> dict:
    payload = _build_searcher_payload(venue_doc, year)
    strategy_slug = str(venue_doc.get("strategy") or "").strip()
    resolved_strategy = _resolve_strategy(strategy_slug) if strategy_slug else {}
    if strategy_slug and not resolved_strategy:
        raise RuntimeError(f"strategy '{strategy_slug}' was not found")

    fetch_step = None
    for step in resolved_strategy.get("steps", []):
        if isinstance(step, dict) and step.get("id") == "fetch_papers":
            fetch_step = step
            break

    fetch_config: dict = {}
    if fetch_step and isinstance(fetch_step.get("config"), dict):
        fetch_config = fetch_step["config"]

    method = str(fetch_config.get("method") or "POST").strip().upper()
    if method not in {"GET", "POST"}:
        raise RuntimeError(f"unsupported strategy fetch method '{method}'")
    base_url = str(fetch_config.get("base_url") or settings.searcher_api_base_url).strip()
    endpoint = str(fetch_config.get("endpoint") or "").strip()
    request_url = _build_searcher_url(base_url, endpoint)
    if not request_url:
        raise RuntimeError("searcher request URL is empty; check SEARCHER_API_BASE_URL or strategy")

    if method == "GET":
        raw_params = fetch_config.get("params")
        if raw_params is None and fetch_config.get("url_source") == "download_sources":
            raw_params = {"url": "{download_sources[year].url}"}
        params = raw_params if isinstance(raw_params, dict) else {}
        resolved_params = _resolve_template(params, payload, venue_doc, year)
        if not isinstance(resolved_params, dict):
            raise RuntimeError("strategy GET params must resolve to an object")
        return {"method": "GET", "url": request_url, "params": resolved_params}

    raw_body = fetch_config.get("body")
    if raw_body is None:
        request_body: object = payload
    else:
        request_body = _resolve_template(raw_body, payload, venue_doc, year)
    return {"method": "POST", "url": request_url, "body": request_body}


def _call_searcher(request_spec: dict) -> dict | list:
    method = str(request_spec.get("method") or "POST").upper()
    url = str(request_spec.get("url") or "").strip()
    if not url:
        raise RuntimeError("searcher request URL is missing")

    headers = {"Accept": "application/json"}
    request_data = None
    request_url = url
    if method == "GET":
        params = request_spec.get("params", {})
        query_items: list[tuple[str, str]] = []
        if isinstance(params, dict):
            for key, raw_value in params.items():
                if raw_value is None:
                    continue
                if isinstance(raw_value, list):
                    for item in raw_value:
                        if item is not None:
                            query_items.append((str(key), str(item)))
                else:
                    query_items.append((str(key), str(raw_value)))
        if query_items:
            query = urllib_parse.urlencode(query_items, doseq=True)
            joiner = "&" if "?" in request_url else "?"
            request_url = f"{request_url}{joiner}{query}"
    elif method == "POST":
        headers["Content-Type"] = "application/json"
        request_data = json.dumps(request_spec.get("body", {})).encode("utf-8")
    else:
        raise RuntimeError(f"unsupported HTTP method '{method}'")

    req = urllib_request.Request(
        url=request_url,
        data=request_data,
        headers=headers,
        method=method,
    )
    try:
        with urllib_request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8").strip()
    except urllib_error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore").strip()
        detail = err_body or exc.reason or "HTTP error"
        raise RuntimeError(f"searcher API returned {exc.code}: {detail}") from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f"searcher API request failed: {exc.reason}") from exc

    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("searcher API returned non-JSON response") from exc
    if isinstance(parsed, (dict, list)):
        return parsed
    raise RuntimeError("searcher API returned unsupported JSON payload")


async def _search_papers_for_venue(venue_doc: dict, year: int) -> tuple[dict | list, list[dict]]:
    request_spec = _build_searcher_request(venue_doc, year)
    searcher_response = await asyncio.to_thread(_call_searcher, request_spec)
    return searcher_response, _extract_response_papers(searcher_response)


def _extract_response_papers(response_payload: dict | list) -> list[dict]:
    if isinstance(response_payload, list):
        return [item for item in response_payload if isinstance(item, dict)]
    if isinstance(response_payload, dict):
        for key in ("papers", "results", "data"):
            items = response_payload.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
    return []


def _coerce_authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(author).strip() for author in value if str(author).strip()]


def _coerce_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(tag).strip() for tag in value if str(tag).strip()]


def _to_paper_model(raw: dict, venue_doc: dict, year: int) -> Paper | None:
    doi = str(raw.get("doi") or raw.get("DOI") or "").strip()
    if not doi:
        return None
    publication_year = raw.get("publication_year", raw.get("year", year))
    if not isinstance(publication_year, int):
        publication_year = year
    try:
        return Paper(
            doi=doi,
            title=str(raw.get("title") or "").strip(),
            authors=_coerce_authors(raw.get("authors")),
            publication_year=publication_year,
            source=str(raw.get("source") or "searcher").strip(),
            url=str(raw.get("url") or "").strip(),
            pdf_link=str(raw.get("pdf_link") or "").strip(),
            pdf_path=str(raw.get("pdf_path") or "").strip(),
            venue=str(raw.get("venue") or venue_doc.get("short_name") or "").strip(),
            snippet=str(raw.get("snippet") or "").strip(),
            is_abstract=bool(raw.get("is_abstract", False)),
            tags=_coerce_tags(raw.get("tags")),
            title_slug=str(raw.get("title_slug") or "").strip(),
            ingested=bool(raw.get("ingested", False)),
        )
    except Exception:
        return None


def _extract_downloaded_count(response_payload: dict | list, fallback_count: int) -> int:
    if isinstance(response_payload, dict):
        raw = response_payload.get("downloaded_papers", response_payload.get("downloaded_count"))
        if isinstance(raw, int) and raw >= 0:
            return raw
    return fallback_count


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
async def get_prefill(name: str, existing_tags: list[str] | None = Query(default=None)):
    tags = [t.strip() for t in (existing_tags or []) if t and t.strip()]
    return prefill_venue(name, existing_tags=tags or None)



@router.post("", status_code=201)
async def create_venue(venue: VenueRecord):
    slug = _slug(venue.short_name)
    if not slug:
        raise HTTPException(status_code=422, detail="short_name produced an empty slug")
    try:
        path = _venue_path(slug)
        path.parent.mkdir(parents=True, exist_ok=True)
        existing_doc = _load_venue_doc(path) if path.exists() else {}
        data = venue.model_dump()
        data["tags"] = _sanitize_tags(data.get("tags", []))
        data["slug"] = slug
        if not data.get("strategy", "").strip():
            data["strategy"] = _default_strategy_for_slug(slug)
        for field in _INTERNAL_VENUE_FIELDS:
            data[field] = existing_doc.get(field, data.get(field, {}))
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
                "strategy": d.get("strategy", ""),
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


@router.get("/{slug}/paper-downloads")
async def get_paper_downloads(slug: str):
    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    doc = _load_venue_doc(path)
    if doc.get("type") != "conference":
        raise HTTPException(status_code=400, detail="paper downloads are only supported for conference venues")

    stats = _normalize_download_stats(doc.get("paper_downloads", {}))
    years = _conference_years(doc)
    cache_counts = await mongo.get_search_cache_counts(slug, years)
    rows = []
    for year in years:
        key = str(year)
        row = stats.get(
            key,
            {
                "downloaded_papers": 0,
                "last_attempted_at": "",
                "last_status": "",
                "last_error": "",
            },
        )
        rows.append({"year": year, "found_papers": cache_counts.get(year), **row})

    return {
        "slug": slug,
        "short_name": doc.get("short_name", slug),
        "long_name": doc.get("long_name", ""),
        "type": doc.get("type", ""),
        "years": rows,
    }


@router.get("/{slug}/paper-search/{year}")
async def search_papers_for_conference_year(slug: str, year: int):
    parsed_year = _parse_year(year)
    if parsed_year is None:
        raise HTTPException(
            status_code=422,
            detail=f"year must be between {_DOWNLOAD_YEAR_MIN} and next calendar year",
        )

    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    doc = _load_venue_doc(path)
    if doc.get("type") != "conference":
        raise HTTPException(status_code=400, detail="paper search is only supported for conference venues")

    try:
        _, paper_candidates = await _search_papers_for_venue(doc, parsed_year)
        return {
            "slug": slug,
            "year": parsed_year,
            "total": len(paper_candidates),
            "papers": paper_candidates,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"failed to fetch papers from external searcher API: {exc}",
        ) from exc


@router.post("/{slug}/paper-search/{year}")
async def search_and_cache_papers_for_conference_year(slug: str, year: int):
    parsed_year = _parse_year(year)
    if parsed_year is None:
        raise HTTPException(
            status_code=422,
            detail=f"year must be between {_DOWNLOAD_YEAR_MIN} and next calendar year",
        )

    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    doc = _load_venue_doc(path)
    if doc.get("type") != "conference":
        raise HTTPException(status_code=400, detail="paper search is only supported for conference venues")

    try:
        _, paper_candidates = await _search_papers_for_venue(doc, parsed_year)
        await mongo.upsert_search_cache(slug, parsed_year, paper_candidates)
        return {
            "slug": slug,
            "year": parsed_year,
            "total": len(paper_candidates),
            "papers": paper_candidates,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"failed to fetch papers from external searcher API: {exc}",
        ) from exc


@router.post("/{slug}/paper-downloads/{year}")
async def download_papers_for_conference_year(slug: str, year: int):
    parsed_year = _parse_year(year)
    if parsed_year is None:
        raise HTTPException(
            status_code=422,
            detail=f"year must be between {_DOWNLOAD_YEAR_MIN} and next calendar year",
        )

    path = _venue_path(slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Venue '{slug}' not found")
    doc = _load_venue_doc(path)
    if doc.get("type") != "conference":
        raise HTTPException(status_code=400, detail="paper downloads are only supported for conference venues")

    attempted_at = _utc_now_iso()
    stats = _normalize_download_stats(doc.get("paper_downloads", {}))
    year_key = str(parsed_year)

    try:
        searcher_response, paper_candidates = await _search_papers_for_venue(doc, parsed_year)
        papers: list[Paper] = []
        for candidate in paper_candidates:
            paper = _to_paper_model(candidate, doc, parsed_year)
            if paper is not None:
                papers.append(paper)

        bulk_result = {"upserted": 0, "modified": 0, "errors": []}
        if papers:
            bulk_result = await mongo.bulk_upsert(
                papers,
                overwrite_missing_fields=False,
                overwrite_duplicate_doi=True,
            )

        downloaded_count = _extract_downloaded_count(searcher_response, fallback_count=len(papers))
        stats[year_key] = {
            "downloaded_papers": downloaded_count,
            "last_attempted_at": attempted_at,
            "last_status": "success",
            "last_error": "",
        }
        doc["paper_downloads"] = stats
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return {
            "slug": slug,
            "year": parsed_year,
            "downloaded_papers": downloaded_count,
            "last_attempted_at": attempted_at,
            "bulk_upsert": bulk_result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        stats[year_key] = {
            "downloaded_papers": 0,
            "last_attempted_at": attempted_at,
            "last_status": "error",
            "last_error": str(exc),
        }
        doc["paper_downloads"] = stats
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        raise HTTPException(
            status_code=502,
            detail="failed to fetch conference papers from external searcher API",
        ) from exc


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
        existing_doc = _load_venue_doc(path)
        data = venue.model_dump()
        data["tags"] = _sanitize_tags(data.get("tags", []))
        data["slug"] = slug
        if not data.get("strategy", "").strip():
            data["strategy"] = _default_strategy_for_slug(slug)
        for field in _INTERNAL_VENUE_FIELDS:
            data[field] = existing_doc.get(field, data.get(field, {}))
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
