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
