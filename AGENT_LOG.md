# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

---

## [2026-05-31] claude-sonnet-4-6 — add download strategy system with inheritance and management UI

**Action:** Implemented a JSON-based strategy system for conference paper download workflows. Each strategy is stored as a `strategies/<slug>.json` file. Strategies can inherit from a parent via `extends` and override individual steps by `id`. A resolved endpoint merges the full inheritance chain before returning. Added `Strategy` and `StrategyStep` Pydantic models, a full CRUD API at `/api/strategies`, a `strategy` field on `VenueRecord`, and two new pages: `/strategies` (list + create) and `/strategies/{slug}` (edit with Human Readable, JSON Editor, and Resolved View tabs). Seeded `_default.json` and `ieee_xplore.json` as starter strategies.

**Files changed:**
- `strategies/_default.json` — base strategy (fetch, DOI resolve, citations, upsert)
- `strategies/ieee_xplore.json` — extends _default, overrides fetch step for IEEE Xplore
- `strategies/.gitkeep` — tracks directory in git
- `services/models.py` — added `StrategyStep`, `Strategy` models; added `strategy` field to `VenueRecord`
- `config/settings.py` — added `STRATEGIES_DIR` path constant
- `api/routes/strategies.py` — new router with CRUD + `/resolved` endpoint; merge-by-id inheritance logic
- `api/main.py` — registered strategies router; added `/strategies` and `/strategies/{slug}` page routes
- `api/routes/venues.py` — added `strategy` to list payload
- `api/static/strategies.html` — strategy list and create page
- `api/static/strategy.html` — three-tab detail/edit page (human readable, JSON editor, resolved view)
- `api/static/venue.html` — strategy selector dropdown with link to strategy page
- `api/static/conf.html`, `venues.html`, `journals.html`, `addconf.html`, `addjournal.html` — Strategies nav link added
- `VERSION.md` — bumped to `paper-library-v0.1.60`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Steps merged by `id` (descendant overrides ancestor with same id; new ids appended). `_default` cannot be deleted. Strategy row hidden on journal edit pages. `strategies/` files are committed to git so strategies are version-controlled alongside code.

**Open items:** The `update.sh` deploy script should `chown paperuser:paperuser /opt/paper-library/strategies` on existing deployments if the directory needs write access (strategies are read-only at runtime currently — writes come through the API running as paperuser, which owns the checkout).

---

## [2026-05-31] claude-sonnet-4-6 — fix typo in default SEARCHER_API_BASE_URL

**Action:** Corrected "seracher" → "searcher" in the default `SEARCHER_API_BASE_URL` value in `config/settings.py` and `.env.example`. The typo would cause all Get Papers requests to fail silently unless the env var was explicitly set.

**Files changed:**
- `config/settings.py` — fixed default URL spelling
- `.env.example` — fixed URL spelling
- `VERSION.md` — bumped to `paper-library-v0.1.59`
- `AGENT_LOG.md` — prepended this entry

**Open items:** None.

---

## [2026-05-31] codex-gpt-5 — add conference Get Papers workflow with per-year status

**Action:** Added a conference paper download flow backed by a new `/getpapers/{slug}` page and new venue API endpoints for fetching per-year download status and triggering downloads. The backend now calls the external searcher API (`SEARCHER_API_BASE_URL`, default `https://seracher.xds-lab.com`), bulk-upserts returned papers, and stores per-year metrics (`downloaded_papers`, `last_attempted_at`, status/error) in venue JSON. Added “Get Papers” actions on conference rows and preserved internal `paper_downloads` metadata during venue create/update writes.

**Files changed:**
- `api/routes/venues.py` — added paper download helpers and `GET/POST /api/venues/{slug}/paper-downloads...`; preserves internal metadata in create/update
- `api/main.py` — added `/getpapers/{slug}` page route
- `api/static/getpapers.html` — new conference download/status page
- `api/static/conf.html` — added `Get Papers` action button
- `api/static/venues.html` — added `Get Papers` action button for conference rows
- `api/static/venue.html` — added conference-only `Get Papers` shortcut link
- `config/settings.py` — added `searcher_api_base_url` setting
- `.env.example` — documented `SEARCHER_API_BASE_URL`
- `.env.dev` — mirrored `SEARCHER_API_BASE_URL`
- `ARCHITECTURE.md` — documented new endpoints, route, metadata, and config
- `VERSION.md` — bumped to `paper-library-v0.1.58`

**Decisions:** Implemented external API calls with stdlib `urllib` inside `asyncio.to_thread` to avoid adding dependencies. Kept download metadata as an internal JSON field (`paper_downloads`) instead of altering `VenueRecord` and explicitly preserved it on venue writes so UI edits do not erase operational history.

**Open items:** External API schema is not documented in-repo; current implementation expects a JSON response with either `papers`, `results`, `data`, or a top-level list. If the remote service uses a different path/payload contract, set `SEARCHER_API_BASE_URL` to the correct endpoint and adjust mapping logic.

## [2026-05-31] codex-gpt-5 — add click-to-sort ascending/descending on venue tables

**Action:** Added client-side table sorting to the three venue listing pages (`/venues`, `/conferences`, `/journals`). Users can now click sortable column headers to toggle ascending/descending order. Sorting is applied after existing search and tag filters so current filter behavior is preserved.

**Files changed:**
- `api/static/venues.html` — sortable headers and sort state/comparators for all data columns (excluding Actions)
- `api/static/conf.html` — sortable headers and sort state/comparators for conference columns
- `api/static/journals.html` — sortable headers and sort state/comparators for journal columns
- `VERSION.md` — bumped to `paper-library-v0.1.57`

**Decisions:** Used per-page in-browser sorting state (`sortKey`, `sortDir`) with visual indicators (`▲`/`▼`) on active headers. Submission deadline sorting uses calendar month order rather than alphabetical order on pages where that column exists.

**Open items:** None.

---

## [2026-05-31] codex-gpt-5 — fix stale prefill tags and robust existing_tags transport

**Action:** Applied follow-up fixes to the Claude tag-input changes. Updated prefill request transport to send repeated `existing_tags` query params (instead of comma-joining) so tags with commas round-trip correctly. Updated add/edit pages so `loadTagSuggestions([])` clears stale text field state rather than preserving previous tags when prefill returns none.

**Files changed:**
- `api/routes/venues.py` — `GET /api/venues/prefill` now accepts `existing_tags: list[str]` query params via FastAPI `Query`
- `api/static/addconf.html` — switched prefill URL building to `URLSearchParams` with repeated `existing_tags`; always sync/clear `#f-tags` in `loadTagSuggestions`
- `api/static/addjournal.html` — same fixes as `addconf.html`
- `api/static/venue.html` — always sync/clear `#f-tags` in `loadTagSuggestions`
- `ARCHITECTURE.md` — documented optional repeated `existing_tags` query params for prefill
- `VERSION.md` — bumped to `paper-library-v0.1.56`

**Decisions:** Kept endpoint semantics GET-based and backward-compatible with existing `name` parameter while changing the optional tag transport shape to avoid delimiter ambiguity.

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — AI prefill suggests tags from existing list, adds new ones if needed

**Action:** Updated `prefill_venue` to accept an optional `existing_tags` list and include it in the LLM user message. Updated the prompt to instruct the model to prefer existing tags where they fit and only add new tags when the existing set is insufficient. Updated `GET /api/venues/prefill` to accept an `existing_tags` query param. Updated `doPrefill` in `addconf.html` and `addjournal.html` to fetch the full tag list and pass it to the prefill endpoint before calling populate.

**Files changed:**
- `services/venues.py` — `prefill_venue` accepts `existing_tags`; prompt updated with tag rules; `tags` added to JSON key list
- `api/routes/venues.py` — `get_prefill` accepts and forwards `existing_tags` query param
- `api/static/addconf.html` — `doPrefill` fetches tags and appends `existing_tags` to prefill URL
- `api/static/addjournal.html` — same
- `VERSION.md` — bumped to `paper-library-v0.1.55`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Tags fetch failure is silently ignored so prefill still works when the tags file doesn't exist yet. Existing tags are sent as a comma-separated query param to keep the endpoint a simple GET.

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — replace tag checkboxes with text input and top-10 suggestion chips

**Action:** Replaced the checkbox-based tag picker in addconf.html, addjournal.html, and venue.html with a text input (semicolon-separated) plus clickable suggestion chips showing the top 10 known tags. Chips toggle their tag into/out of the text field and highlight blue when active.

**Files changed:**
- `api/static/addconf.html` — new tag input + suggestion chips UI
- `api/static/addjournal.html` — same
- `api/static/venue.html` — same
- `VERSION.md` — bumped to `paper-library-v0.1.54`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `parseTags` splits on `;` and trims whitespace; `serializeTags` joins with `"; "`. Chip state is re-evaluated on every toggle by re-reading the text field, so manual edits and chip clicks stay in sync.

**Open items:** None.

---

## [2026-05-31] codex-gpt-5 — harden venue tag APIs and cascade tag deletion

**Action:** Implemented the requested review fixes: robust tag validation/normalization, defensive `_tags.json` parsing, cascade removal of deleted tags from all saved venue files, and generic non-leaky 500 error messages for venue create/update writes.

**Files changed:**
- `api/routes/venues.py` — added tag normalization/validation helpers; sanitized tag reads/writes; cascaded tag delete across `venues/*.json`; replaced `detail=str(exc)` with generic write-failure messages
- `ARCHITECTURE.md` — updated venue endpoint map (including tags + PUT), venue summary fields, and tag lifecycle constraints/cascade behavior
- `VERSION.md` — bumped to `paper-library-v0.1.53`

**Decisions:** Tag names are now constrained to non-empty, max 64 chars, and cannot contain `/` or `\` to keep delete semantics safe with path params. Existing malformed tag values in files are ignored/sanitized rather than causing endpoint failures.

**Open items:** None.

---

## [2026-05-31] codex-gpt-5 — reviewed recent Claude venue/tag changes for regressions

**Action:** Performed a code review of recent Claude-authored updates (venue tags system, new routes/pages, and listing/filter UI) and identified functional and robustness issues requiring fixes.

**Files changed:**
- `AGENT_LOG.md` — prepended this review handoff entry

**Decisions:** Review-only pass; no application code edits were made in this step.

**Open items:** Fixes are needed for tag lifecycle consistency and tag identifier validation (see review findings in assistant response).

---

## [2026-05-31] claude-sonnet-4-6 — add venue tagging system with tag management page and filters

**Action:** Added a full tagging system for venues. Tags are stored in `venues/_tags.json` as a sorted list. Added `tags: list[str]` to `VenueRecord`. Added three API endpoints: `GET /api/venues/tags`, `POST /api/venues/tags`, `DELETE /api/venues/tags/{tag}`. Created `tags.html` for adding/deleting tags. Added tag checkbox picker to `addconf.html`, `addjournal.html`, and `venue.html`. Added clickable tag filter chips and a Tags column to all three listing pages. Added `/tags` page route and Tags nav link across all pages.

**Files changed:**
- `services/models.py` — added `tags` field to `VenueRecord`
- `api/routes/venues.py` — added `_load_tags`, `_save_tags` helpers; added `GET/POST /tags` and `DELETE /tags/{tag}` endpoints; added `tags` to list payload
- `api/main.py` — added `/tags` page route
- `api/static/tags.html` — new tag management page
- `api/static/addconf.html` — tag picker, Tags nav link
- `api/static/addjournal.html` — tag picker, Tags nav link
- `api/static/venue.html` — tag picker, Tags nav link
- `api/static/venues.html` — tag filter chips, Tags column, Tags nav link
- `api/static/conf.html` — tag filter chips, Tags column, Tags nav link
- `api/static/journals.html` — tag filter chips, Tags column, Tags nav link
- `VERSION.md` — bumped to `paper-library-v0.1.52`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Tags stored in `_tags.json` inside the venues directory — no new directory or database needed. Clicking an active tag chip deselects it (toggle). Tags in listing pages fetched in parallel with venues for minimal latency.

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — set /venues as root homepage

**Action:** Changed the root `/` redirect from `/docs` to `/venues`.

**Files changed:**
- `api/main.py` — root redirect updated
- `VERSION.md` — bumped to `paper-library-v0.1.51`
- `AGENT_LOG.md` — prepended this entry

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — remove max-width cap from listing pages

**Action:** Removed `max-width:900px` from `.card` and `.toolbar` in venues.html, conf.html, and journals.html so the tables fill the full page width.

**Files changed:**
- `api/static/venues.html` — removed max-width from .card and .toolbar
- `api/static/conf.html` — same
- `api/static/journals.html` — same
- `VERSION.md` — bumped to `paper-library-v0.1.50`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** No max-width constraint applied; tables expand to body padding boundary.

**Open items:** None.

---

