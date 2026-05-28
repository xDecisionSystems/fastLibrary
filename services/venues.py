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


def _ieee_xplore_lookup(name: str, venue_type: str) -> str:
    """Query IEEE Xplore API for the proceedings/journal URL. Returns "" on any failure."""
    if not settings.ieee_xplore_api_key:
        return ""
    try:
        params = urllib.parse.urlencode({
            "querytext": name,
            "max_records": 5,
            "apikey": settings.ieee_xplore_api_key,
        })
        if venue_type == "journal":
            url = f"{_IEEE_XPLORE_BASE}/search/articles?{params}&content_type=Journals"
        else:
            url = f"{_IEEE_XPLORE_BASE}/search/articles?{params}&content_type=Conferences"

        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())

        articles = data.get("articles", [])
        if not articles:
            return ""

        # For conferences: use publication_number to build the all-proceedings URL
        # For journals: use punumber to build the journal home URL
        first = articles[0]
        if venue_type == "journal":
            punumber = first.get("punumber", "")
            if punumber:
                return f"https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber={punumber}"
        else:
            publication_number = first.get("publication_number", "")
            if publication_number:
                return f"https://ieeexplore.ieee.org/xpl/conhome/{publication_number}/all-proceedings"

        return ""
    except Exception:
        return ""


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

        # If IEEE publisher, look up the authoritative URL from IEEE Xplore API
        publisher = result.get("publisher", "")
        if "ieee" in publisher.lower() and settings.ieee_xplore_api_key:
            xplore_url = _ieee_xplore_lookup(name, result.get("type", ""))
            if xplore_url:
                result["access_url"] = xplore_url

        return result
    except Exception as exc:
        return {"error": "prefill failed", "detail": str(exc)}
