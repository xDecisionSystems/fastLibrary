import json
import re

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
- access_url: homepage URL if known, else ""
- open_access: true or false
- notes: any brief relevant note, else ""
- download_sources: array of {name, url, notes} objects for bulk download sources (e.g. IEEE Xplore, ACM DL), or []

Respond ONLY with valid JSON. No markdown fences, no explanation."""


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
        # Strip markdown fences if the model ignores the instruction
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw.strip())
        raw = re.sub(r"\n?```$", "", raw.strip())
        return json.loads(raw)
    except Exception as exc:
        return {"error": "prefill failed", "detail": str(exc)}
