# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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

## [2026-05-31] claude-sonnet-4-6 — fix create_venue returning non-JSON 500 on filesystem error

**Action:** Wrapped the `create_venue` handler body in a try/except so any filesystem exception raises an `HTTPException(500)` with a JSON detail body rather than letting FastAPI emit a plain-text 500 page. The browser-side error "Unexpected token 'I', 'Internal S'..." was caused by the server returning "Internal Server Error" as plain text instead of JSON.

**Files changed:**
- `api/routes/venues.py` — try/except around file write in `create_venue`
- `VERSION.md` — bumped to `paper-library-v0.1.47`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Root cause on the deployed server is stale code (old `VenueRecord` without `website_url`/`proceedings_url`). This fix also guards against future filesystem errors. Deployed server must be updated via `deploy/update.sh` to resolve the underlying issue.

**Open items:** Run `deploy/update.sh` on the LXC to deploy the new model fields.

---

## [2026-05-31] claude-sonnet-4-6 — rename Notes to Description and update prefill prompt

**Action:** Relabeled the Notes field in addconf.html to "Description" with a placeholder guiding the user to enter a brief scope/focus description. Updated the LLM prefill prompt so the `notes` field is filled with a description rather than a generic note.

**Files changed:**
- `api/static/addconf.html` — label and placeholder updated
- `services/venues.py` — `notes` prompt rule updated
- `VERSION.md` — bumped to `paper-library-v0.1.46`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** The underlying field key stays `notes` to avoid a model/API change; only the UI label and prompt guidance change.

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — repurpose download sources as per-year proceedings in addconf

**Action:** Relabeled the Download Sources table in addconf.html as "Per-Year Proceedings" with a clarifying note that it is only needed when individual years have separate URLs (the top-level Proceedings URL covers all years otherwise). Changed the Name column header and placeholder from "e.g. IEEE Xplore" to "e.g. 2024". The underlying `download_sources` field and data model are unchanged.

**Files changed:**
- `api/static/addconf.html` — section title, help text, column header, and placeholder updated
- `VERSION.md` — bumped to `paper-library-v0.1.45`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Reused `download_sources` rather than adding a new field — the {name, url, notes} shape maps naturally to {year, url, notes}. No model or API changes needed.

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — add website_url and proceedings_url fields to venues

**Action:** Replaced the single `access_url` field with two URL fields: `website_url` (most recent conference/journal home page) and `proceedings_url` (publisher archive page, conferences only). Updated the LLM prefill prompt with rules for both fields. Updated addconf.html with two URL inputs; addjournal.html with one (website only). Updated all three listing pages with a "Links" column showing clickable Website/Proceedings links. Added backward-compatible fallback in list_venues() so existing JSON files with `access_url` still read correctly.

**Files changed:**
- `services/models.py` — replaced `access_url` with `website_url` and `proceedings_url`
- `services/venues.py` — updated prefill prompt keys and rules for both URL fields
- `api/routes/venues.py` — list payload includes `website_url` (with `access_url` fallback) and `proceedings_url`
- `api/static/addconf.html` — two URL inputs (Conference Website, Proceedings URL); populate/getForm/clearForm updated
- `api/static/addjournal.html` — single URL input (Journal Website); `proceedings_url` sent as ""
- `api/static/conf.html` — "Links" column with Website / Proceedings links
- `api/static/venues.html` — "Links" column with Website / Proceedings links
- `api/static/journals.html` — "Website" column replacing unused Submission Deadline column
- `VERSION.md` — bumped to `paper-library-v0.1.44`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Kept `access_url` fallback in list_venues() so existing venue JSON files are not broken. Journals show a Website column instead of Submission Deadline since that field is n/a for journals.

**Open items:** Existing venue JSON files still store `access_url`; they will display correctly via the fallback but will lose the value if re-saved through the new form (user must re-enter the URL). A one-time migration script could rename the field in all JSON files if needed.

---

