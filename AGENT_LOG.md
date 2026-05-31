# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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

## [2026-05-31] claude-sonnet-4-6 — add venue detail/edit page at /venues/{slug}

**Action:** Added `PUT /api/venues/{slug}` update endpoint. Added `/venues/{slug}` page route in `main.py` serving a new `venue.html`. The page loads the record on arrival, populates all fields as editable inputs (same fields as addconf/addjournal), hides Submission Deadline for journals, and saves via PUT. Updated View buttons in all three listing pages to navigate to `/venues/{slug}` instead of the raw JSON endpoint.

**Files changed:**
- `api/routes/venues.py` — added `PUT /{slug}` update endpoint
- `api/main.py` — added `/venues/{slug}` page route
- `api/static/venue.html` — new detail/edit page
- `api/static/conf.html` — View link → `/venues/${v.slug}`
- `api/static/venues.html` — View link → `/venues/${v.slug}`
- `api/static/journals.html` — View link → `/venues/${v.slug}`
- `VERSION.md` — bumped to `paper-library-v0.1.49`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** The page derives the slug from `location.pathname` so no extra routing state is needed. Revert button re-fetches from the API, discarding unsaved changes.

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — create venues/ directory with correct ownership in deploy scripts

**Action:** Added `venues/` directory creation (owned by `paperuser`) to both deploy scripts. `proxmox_deploy.sh` creates it alongside `pdf/` on fresh installs. `update.sh` ensures it exists with correct ownership on every update, fixing the `[Errno 13] Permission denied: 'venues/dasc.json'` error on existing deployments.

**Files changed:**
- `deploy/proxmox_deploy.sh` — added `venues/` to data directory creation block
- `deploy/update.sh` — added data directory ensure step after git pull
- `VERSION.md` — bumped to `paper-library-v0.1.48`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Placed the fix in `update.sh` so existing LXCs are corrected automatically on next `update.sh` run without manual intervention.

**Open items:** None.

---

