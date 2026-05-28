import json
import re
import urllib.parse
import urllib.request

from openai import AzureOpenAI

from config.settings import settings

_VENUE_PREFILL_PROMPT = """\
You are a research database assistant. Given a conference or journal name, return a JSON object with these exact keys:
  short_name, long_name, type, publisher, access_url, open_access, notes, download_sources

Rules:
- short_name: standard acronym (e.g. ICRA, NeurIPS, TRO, IJRR)
- long_name: full official name
- type: "conference" or "journal"
- publisher: publishing organization (e.g. IEEE, ACM, Springer)
- access_url: leave "" if not certain — do not guess
- open_access: true or false
- notes: any brief relevant note, else ""
- download_sources: array of {name, url, notes} objects for bulk download sources (e.g. IEEE Xplore, ACM DL), or []

Respond ONLY with valid JSON. No markdown fences, no explanation."""

_IEEE_XPLORE_BASE = "https://ieeexploreapi.ieee.org/api/v1"


def _ieee_fetch_articles(name: str, venue_type: str, max_records: int = 100) -> list:
    """Fetch articles from IEEE Xplore API. Returns empty list on any failure."""
    if not settings.ieee_xplore_api_key:
        return []
    content_type = "Journals" if venue_type == "journal" else "Conferences"
    params = urllib.parse.urlencode({
        "querytext": name,
        "max_records": max_records,
        "content_type": content_type,
        "apikey": settings.ieee_xplore_api_key,
    })
    url = f"{_IEEE_XPLORE_BASE}/search/articles?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode())
    return data.get("articles", [])


def ieee_proceedings_urls(name: str, venue_type: str) -> list[dict]:
    """Return a list of {year, label, url} for all unique per-year proceedings.

    For conferences: one entry per unique publication_number, sorted by year desc.
    For journals: single entry pointing to the journal home page.
    Returns [] if IEEE Xplore API key is not configured or lookup fails.
    """
    if not settings.ieee_xplore_api_key:
        return []
    try:
        articles = _ieee_fetch_articles(name, venue_type, max_records=100)
        if not articles:
            return []

        if venue_type == "journal":
            punumber = articles[0].get("publication_number", "")
            if not punumber:
                return []
            return [{
                "year": None,
                "label": articles[0].get("publication_title", name),
                "url": f"https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber={punumber}",
            }]

        # Build keyword filter from significant words in the query (4+ chars)
        _STOPWORDS = {"ieee", "aiaa", "acm", "conference", "international", "proceedings",
                      "annual", "symposium", "workshop", "journal", "transactions", "systems",
                      "with", "from", "for", "and", "the", "on", "of", "in", "at"}
        keywords = {w.lower() for w in re.split(r"\W+", name) if len(w) >= 4 and w.lower() not in _STOPWORDS}

        # Deduplicate by publication_number, keeping the richest title per number
        seen: dict[int, dict] = {}
        for a in articles:
            pub_num = a.get("publication_number")
            pub_year = a.get("publication_year")
            if not pub_num or not pub_year:
                continue
            pub_num = int(pub_num)
            pub_year = int(pub_year)
            if pub_num not in seen:
                seen[pub_num] = {
                    "year": pub_year,
                    "label": a.get("publication_title", str(pub_year)),
                    "url": f"https://ieeexplore.ieee.org/xpl/conhome/{pub_num}/all-proceedings",
                }

        # Filter to entries whose label shares at least one keyword with the query
        results = [
            v for v in seen.values()
            if not keywords or any(kw in v["label"].lower() for kw in keywords)
        ]
        return sorted(results, key=lambda x: x["year"], reverse=True)
    except Exception:
        return []



def prefill_venue(name: str) -> dict:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        return {"error": "prefill unavailable", "detail": "Azure OpenAI credentials not configured"}
    try:
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        response = client.chat.completions.create(
            model=settings.chat_deployment_name,
            messages=[
                {"role": "system", "content": _VENUE_PREFILL_PROMPT},
                {"role": "user", "content": name},
            ],
            max_completion_tokens=512,
        )
        raw = response.choices[0].message.content or ""
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw.strip())
        raw = re.sub(r"\n?```$", "", raw.strip())
        result = json.loads(raw)

        publisher = result.get("publisher", "")
        if "ieee" in publisher.lower() and settings.ieee_xplore_api_key:
            urls = ieee_proceedings_urls(name, result.get("type", ""))
            if urls:
                result["ieee_proceedings_urls"] = urls

        return result
    except Exception as exc:
        return {"error": "prefill failed", "detail": str(exc)}
