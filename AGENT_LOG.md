# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

---

## [2026-05-31] codex-gpt-5 — wire strategy execution into paper search/download and fix Found semantics

**Action:** Implemented strategy-driven search execution in venue paper search/download flows so fetch behavior now follows resolved strategy config (`method`, `endpoint`, `base_url`, and templated params/body). Split paper search into side-effect-free `GET /paper-search/{year}` (preview only) and cache-writing `POST /paper-search/{year}` used by the UI. Fixed Found-count semantics to distinguish unknown (`null` / `—`) from valid zero results (`0`). Added strategy delete protection that returns 409 if any venue still references the strategy. Updated architecture docs and bumped patch version.

**Files changed:**
- `api/routes/venues.py` — strategy resolution + templated request builder + GET/POST paper-search split + Found nullable semantics
- `api/routes/strategies.py` — prevent deleting strategies still referenced by venue JSON records
- `api/static/getpapers.html` — Search now uses POST cache endpoint; Found column correctly displays `0` vs `—`
- `ARCHITECTURE.md` — updated searcher default URL, venue/search endpoint contracts, cache semantics, and strategy API docs
- `VERSION.md` — bumped to `paper-library-v0.1.64`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Kept strategy placeholder support intentionally narrow and explicit (`{year}`, `{conference.*}`, `{download_sources[year].*}`) to avoid ambiguous runtime behavior while covering current ATRD/default strategy needs.

**Open items:** If future strategies need richer templating (conditionals/transforms), move placeholder resolution into a dedicated, validated strategy runtime module with schema-level validation.

---

## [2026-05-31] codex-gpt-5 — review Claude strategy/search-cache changes and surface fixes

**Action:** Reviewed the most recent Claude-authored changes called out in `AGENT_LOG.md` (strategy system, ATRD strategy, search preview/cache, and getpapers Found column), then performed a code-level regression/risk analysis across the touched backend and frontend files.

**Files changed:**
- `AGENT_LOG.md` — prepended this review handoff entry and archived older entries per policy
- `history/2026-05.md` — appended AGENT_LOG entries older than the 10 most recent

**Decisions:** Logged review findings without applying application-code edits, so implementation choices remain unchanged until fixes are approved.

**Open items:** High-priority fix needed: wire strategy execution into paper search/download flow (current implementation still hardcodes POST + base URL and ignores venue strategy fetch-step config, so ATRD/GET strategies are not actually used).

---

## [2026-05-31] claude-sonnet-4-6 — add paper_search_cache and Found column on getpapers page

**Action:** Added a `paper_search_cache` MongoDB collection to store search results per `(slug, year)` without touching the main `papers` collection. The search endpoint now saves results to this cache on every call. The paper-downloads endpoint reads cache counts and returns a `found_papers` field per year row. The getpapers UI gains a "Found" column that shows the cached count (populated on load and updated in-place immediately after a search completes).

**Files changed:**
- `services/mongo.py` — added `get_search_cache_collection()`, unique index on `(slug, year)`, and helpers `upsert_search_cache`, `get_search_cache`, `get_search_cache_counts`
- `api/routes/venues.py` — `search_papers_for_conference_year` now calls `mongo.upsert_search_cache`; `get_paper_downloads` now calls `mongo.get_search_cache_counts` and includes `found_papers` in each year row
- `api/static/getpapers.html` — "Found" column added; `load()` maps `found_papers`; `searchYear()` updates the Found cell in-place after a successful search
- `VERSION.md` — bumped to `paper-library-v0.1.63`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Cache is keyed on `(slug, year)` with a unique index — each search overwrites the previous result for that year. `found_papers` shows `—` when no search has been run yet. The Found cell updates immediately on search success without requiring a full page reload.

**Open items:** A future "Download from cache" path could read `paper_search_cache` instead of re-calling the searcher, saving an external API round-trip.

---

## [2026-05-31] claude-sonnet-4-6 — add atrd strategy using /search_atrd_papers endpoint

**Action:** Created `strategies/atrd.json`. Inherits all steps from `_default` (DOI resolve, citation fetch, upsert) and overrides `fetch_papers` to call `GET /search_atrd_papers` on the searcher API. The `url` param is sourced from the venue's `download_sources` entry for the target year. Response fields from the ATRD endpoint (title, authors, section, is_best_paper, full_paper_url, presentation_url) are documented in the step config notes.

**Files changed:**
- `strategies/atrd.json` — new ATRD strategy file
- `VERSION.md` — bumped to `paper-library-v0.1.62`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Used `extends: "_default"` so only the fetch step is overridden; DOI resolution, citation lookup, and upsert are inherited unchanged. The `base_url` is set explicitly to `https://searcher.xds-lab.com/aev/search` since ATRD uses a GET with a `url` query param rather than the default POST body contract.

**Open items:** The ATRD venue record still needs to be created with per-year `download_sources` entries (name = year string, url = ATRD symposium papers page for that year). The `_post_to_searcher` / download flow in `venues.py` also needs to be updated to dispatch GET requests when the strategy step specifies `method: GET`.

---

## [2026-05-31] claude-sonnet-4-6 — add Search Papers button and preview modal to getpapers page

**Action:** Added a "Search Papers" button to each year row on the `/getpapers/{slug}` page. Clicking it calls the new `GET /api/venues/{slug}/paper-search/{year}` endpoint, which runs the same searcher API query as Download but returns the raw paper list without saving anything to MongoDB. Results appear in a modal overlay (DOI, title, authors, year, source columns) so the user can preview what exists before committing a download.

**Files changed:**
- `api/routes/venues.py` — added `GET /{slug}/paper-search/{year}` endpoint (preview-only, no upsert)
- `api/static/getpapers.html` — Search button in Actions column; modal overlay with results table; `searchYear()`, `closeSearchModal()` JS functions; modal CSS

**Decisions:** Endpoint is a GET so it is safe to call repeatedly without side effects. Modal closes on Escape or overlay click. Authors are truncated to 3 + "et al." to keep rows readable.

**Open items:** This is a prerequisite for the ATRD paper download strategy. Next step: define a download strategy that uses the search preview to select papers before triggering the full download.

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

**Action:** Added a conference paper download flow backed by a new `/getpapers/{slug}` page and new venue API endpoints for fetching per-year download status and triggering downloads. The backend now calls the external searcher API (`SEARCHER_API_BASE_URL`, default `https://searcher.xds-lab.com`), bulk-upserts returned papers, and stores per-year metrics (`downloaded_papers`, `last_attempted_at`, status/error) in venue JSON. Added "Get Papers" actions on conference rows and preserved internal `paper_downloads` metadata during venue create/update writes.

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
