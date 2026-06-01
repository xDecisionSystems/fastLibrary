import json
import re

from openai import AzureOpenAI

from config.settings import settings

_VENUE_PREFILL_PROMPT = """\
You are a research database assistant. Given a conference or journal name, return a JSON object with these exact keys:
  short_name, long_name, type, publisher, due_date_month, website_url, proceedings_url, open_access, notes, download_sources, tags

Rules:
- short_name: standard acronym (e.g. ICRA, NeurIPS, TRO, IJRR)
- long_name: full official name
- type: "conference" or "journal"
- publisher: publishing organization (e.g. IEEE, ACM, Springer)
- due_date_month: month name (January..December) of the paper/abstract submission deadline. Use the next upcoming deadline if known; otherwise use the most recently known deadline month. Leave "" if unknown or not applicable (e.g. journals).
- website_url: most recent official conference or journal home page URL (e.g. https://icra2025.ieee.org); leave "" if not certain — do not guess
- proceedings_url: publisher's proceedings page URL where papers are archived (e.g. IEEE Xplore, ACM DL, Springer LNCS page for this venue); leave "" if not certain — do not guess
- open_access: true or false
- notes: brief description of the conference or journal scope and focus area, else ""
- download_sources: array of {name, url, notes} objects for bulk download sources (e.g. IEEE Xplore, ACM DL), or []
- tags: array of short topic/domain tag strings describing the venue's research area. Prefer tags from the provided existing tags list where they fit. Add new tags only when the existing list is insufficient to describe the venue. Use concise lowercase strings (e.g. "robotics", "machine learning", "computer vision"). Return [] if no tags apply.

Respond ONLY with valid JSON. No markdown fences, no explanation."""


_PDF_FILENAME_PROMPT = """\
Generate a short, human-readable filename for an academic paper PDF.

Format: <simple_title>-<first_author_lastname>-<venue_short>-<year>.pdf

Rules:
- simple_title: 3 to 5 lowercase words joined with underscores. Choose the most specific and distinctive nouns and adjectives from the title — the words that best distinguish this paper from others in the same field. Prefer domain-specific technical terms (e.g. uncrewed, untowered, utm, detect_avoid) over generic words (concept, approach, system, integration, analysis, study, method). Drop all filler words (a, an, the, of, for, in, on, with, and, to, at, by).
- first_author_lastname: lowercase last name of the first author only. Remove special characters.
- venue_short: short lowercase abbreviation of the venue (e.g. atrd, icra, dasc). Use the acronym if one is common.
- year: 4-digit year.
- Use underscores within each field, dashes between fields. Only lowercase letters, digits, underscores, and dashes allowed. No spaces or dots except the final .pdf.
- Example for "A Concept for Procedural Terminal Area Airspace Integration of Large Uncrewed Aircraft Systems at Non-Towered Airports": procedures_uncrewed_aircraft_untowered_airports-sievers-atrd-2025.pdf
- Return ONLY the filename. No explanation, no markdown, no quotes."""


def generate_pdf_filename(
    title: str,
    authors: list[str],
    venue: str,
    year: int | str,
) -> str | None:
    """Call Azure OpenAI to generate a clean PDF filename. Returns None on failure."""
    if (
        not settings.azure_openai_endpoint
        or not settings.azure_openai_api_key
        or not settings.chat_deployment_name
    ):
        return None
    first_author = authors[0] if authors else ""
    user_content = f"Title: {title}\nFirst author: {first_author}\nVenue: {venue}\nYear: {year}"
    try:
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        response = client.chat.completions.create(
            model=settings.chat_deployment_name,
            messages=[
                {"role": "system", "content": _PDF_FILENAME_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_completion_tokens=64,
        )
        raw = (response.choices[0].message.content or "").strip().strip('"').strip("'")
        # Validate: must end in .pdf and contain only safe characters
        if re.fullmatch(r"[a-z0-9][a-z0-9_\-]*\.pdf", raw):
            return raw
        return None
    except Exception:
        return None


def prefill_venue(name: str, existing_tags: list[str] | None = None) -> dict:
    if not settings.azure_openai_endpoint or not settings.azure_openai_api_key:
        return {"error": "prefill unavailable", "detail": "Azure OpenAI credentials not configured"}
    try:
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        user_content = name
        if existing_tags:
            user_content += f"\n\nExisting tags: {', '.join(existing_tags)}"
        response = client.chat.completions.create(
            model=settings.chat_deployment_name,
            messages=[
                {"role": "system", "content": _VENUE_PREFILL_PROMPT},
                {"role": "user", "content": user_content},
            ],
            max_completion_tokens=512,
        )
        raw = response.choices[0].message.content or ""
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw.strip())
        raw = re.sub(r"\n?```$", "", raw.strip())
        return json.loads(raw)
    except Exception as exc:
        return {"error": "prefill failed", "detail": str(exc)}
