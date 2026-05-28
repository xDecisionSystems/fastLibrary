# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

---

## [2026-05-27] claude-sonnet-4-6 — filter noisy IEEE Xplore results; surface proceedings errors

**Action:** IEEE Xplore full-text search returns fuzzy matches that include unrelated conferences. Added a keyword filter: significant words (4+ chars, excluding common stopwords) are extracted from the query name, and only entries whose label contains at least one keyword are kept. Also added "systems" to stopwords as it's too generic to discriminate. Separately, made `loadProceedingsUrls` and `populate` async to correctly sequence status messages, and added visible error when no proceedings are found.

**Files changed:**
- `services/venues.py` — keyword filter in `ieee_proceedings_urls`; "systems" in stopwords
- `api/static/addvenue.html` — `populate`/`loadProceedingsUrls` async; status messages for loading/empty/error
- `VERSION.md` — bumped to `paper-library-v0.1.31`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Stopwords exclude common words that appear in many unrelated IEEE venues (systems, international, conference, etc.) so filtering is based on domain-specific terms only (e.g. "avionics", "digital"). Filter falls back to returning all results if no keywords survive stopword removal.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section. IEEE Xplore API key must be added to `/opt/paper-library/.env` on the deployed server (`IEEE_XPLORE_API_KEY=dsf4z95psqjg6zrtej3f6qx2`).

---

## [2026-05-27] claude-sonnet-4-6 — fix proceedings list not appearing after AI prefill

**Action:** Proceedings list was silently empty when the IEEE Xplore API key was unconfigured or returned no results. Added a visible status message during lookup, an error message when results are empty (explaining the likely cause), and made `populate()`/`loadProceedingsUrls()` async so status messages sequence correctly rather than being overwritten.

**Files changed:**
- `api/static/addvenue.html` — `populate` and `loadProceedingsUrls` made async; status messages added for loading, success, and empty-results cases
- `VERSION.md` — bumped to `paper-library-v0.1.30`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** The empty-results message explicitly mentions the IEEE Xplore API key so the user knows what to configure rather than seeing a silent blank.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — update.sh: make Y the default in confirmation prompt

**Action:** Changed confirmation prompt from `[y/N]` to `[Y/n]`; pressing Enter now proceeds with the update. Only an explicit `n`/`no` aborts.

**Files changed:**
- `deploy/update.sh` — prompt changed to `[Y/n]`; case flipped to abort on `n`
- `VERSION.md` — bumped to `paper-library-v0.1.29`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Empty input (Enter) falls through to the `*` catch-all which proceeds, matching standard Unix convention for a capital default.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — update.sh: show version diff and confirm before updating

**Action:** Added a pre-flight confirmation step to `deploy/update.sh`. The script now fetches the remote `VERSION.md` without applying it, prints the current → incoming version transition, and prompts `[y/N]` before proceeding. Answering anything other than `y`/`yes` aborts cleanly with exit 0.

**Files changed:**
- `deploy/update.sh` — fetch remote VERSION.md, print transition, read confirmation prompt
- `VERSION.md` — bumped to `paper-library-v0.1.28`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Used `git show origin/HEAD:VERSION.md` after a quiet fetch to read the incoming version without touching the working tree, so the pre-update `OLD_VERSION` remains accurate even if the user aborts.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — fix access_url overwritten with single-year IEEE URL

**Action:** `prefill_venue` was replacing `access_url` with `urls[0]["url"]` (most recent year only) after fetching IEEE proceedings. Removed that assignment so `access_url` keeps whatever the LLM returned (the all-years parent series URL or blank). Per-year URLs are still returned in `ieee_proceedings_urls` for the checkbox list. Removed the now-unused `_ieee_xplore_lookup` helper.

**Files changed:**
- `services/venues.py` — removed `result["access_url"] = urls[0]["url"]`; removed `_ieee_xplore_lookup`
- `VERSION.md` — bumped to `paper-library-v0.1.27`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** The LLM prompt already instructs the model to leave `access_url` blank if uncertain, so the safest behavior is to never overwrite it with a per-year URL from the API.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — proceedings list: label as clickable link, URL hidden

**Action:** Removed the separate URL text from each proceedings row; the label/name is now the only visible element and is itself the clickable link opening in a new tab. Removed unused `.proc-label` CSS.

**Files changed:**
- `api/static/addvenue.html` — `buildProcList` renders `[cb] label↗` only; `.proc-label` CSS removed
- `VERSION.md` — bumped to `paper-library-v0.1.26`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** URL is preserved in `data-url` on the checkbox for form submission; it just isn't shown in the UI.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — show full URL in proceedings checkbox list

**Action:** Updated each proceedings checkbox row to display the label and the full URL as separate elements. The label (year + title) appears as plain text; the URL appears beside it as a clickable link opening in a new tab. Added subtle row separators and `word-break:break-all` so long URLs don't overflow.

**Files changed:**
- `api/static/addvenue.html` — `buildProcList` renders `[cb] label  url↗`; CSS updated for two-column row layout
- `VERSION.md` — bumped to `paper-library-v0.1.25`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Label and URL are separate DOM nodes so the checkbox data-* attributes still store the canonical label/url independently of display formatting.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — proceedings checkbox controls: toggle-all and years-since filter

**Action:** Added "Select / Deselect All" toggle button and "Years since" number input to the proceedings checkbox list header. The years-since input checks only years >= the entered value on each keystroke; clearing it re-checks all items. Removed the year-range (start/end) text boxes from the form. Cleaned up all related CSS, JS helpers (`toggleAllYears`), and `clearForm`/`getForm`/`populate` references to year_start/year_end/all_years.

**Files changed:**
- `api/static/addvenue.html` — toggle-all button, years-since input, `toggleAllProc()`, `applyYearsSince()`; year-range fields removed
- `VERSION.md` — bumped to `paper-library-v0.1.24`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `applyYearsSince` re-checks all boxes when the field is cleared (empty or NaN) so the user can reset to all-selected without clicking the toggle button. Toggle-all detects current state (all checked → deselect all, else → select all).

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — replace Access URL dropdown with checkbox list in addvenue.html

**Action:** Replaced the `<select>` dropdown (per-year proceedings URLs) with a scrollable checkbox list. Each item is checked by default, shows year prepended to the label, and links to the proceedings URL in a new tab. `getForm()` now collects only checked items into `proceedings_years: [{year, label, url}]` which maps to the `VenueRecord.proceedings_years` field added to `services/models.py` in the prior session. `clearForm()` and `populate()` updated accordingly.

**Files changed:**
- `api/static/addvenue.html` — checkbox list replaces dropdown; `buildProcList()` helper; `getForm()` collects `proceedings_years`; `clearForm()` clears list
- `VERSION.md` — bumped to `paper-library-v0.1.23`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Year is always prepended to the display label (even when the IEEE title already contains it) so each row is unambiguous when skimming. Items use `data-*` attributes on the checkbox to avoid re-reading the DOM at submit time.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section (noted in prior sessions).

---

## [2026-05-27] claude-sonnet-4-6 — set default REPO_URL in proxmox_deploy.sh

**Action:** Set `REPO_URL` default to `https://github.com/xDecisionSystems/fastLibrary` in `deploy/proxmox_deploy.sh` so the deploy script no longer prompts for the repo URL when using the canonical repository.

**Files changed:**
- `deploy/proxmox_deploy.sh` — `REPO_URL` default set to canonical GitHub URL
- `VERSION.md` — bumped to `paper-library-v0.1.7`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** The `--repo-url` flag and `REPO_URL` env var still override the default, so non-canonical forks remain fully supported.

**Open items:** None.

---

## [2026-05-27] claude-sonnet-4-6 — venue management feature (JSON store, API, browser UI)

**Action:** Implemented the full venue management feature: JSON file store at `venues/<slug>.json`, five FastAPI CRUD + prefill endpoints under `/venues`, Azure OpenAI LLM prefill for venue metadata, and four browser-served HTML pages (`/addvenue`, `/venues/ui`, `/conf`, `/journals`). Added `DownloadSource` and `VenueRecord` Pydantic models. Updated settings to include Azure OpenAI credentials and `VENUES_DIR`. Added `openai` and `aiofiles` to requirements.

**Files changed:**
- `venues/.gitkeep` — created; venues/ directory tracked in repo
- `.gitignore` — added `venues/*.json` so venue data is not committed
- `config/settings.py` — added `venues_dir`, `azure_openai_endpoint`, `azure_openai_api_key`, `azure_openai_api_version`, `chat_deployment_name`
- `.env.example` — documented `VENUES_DIR` and all four Azure OpenAI vars
- `services/models.py` — added `DownloadSource` and `VenueRecord` models
- `services/venues.py` — created; `prefill_venue(name)` using Azure OpenAI chat, non-blocking on credential absence or LLM error
- `api/routes/venues.py` — created; `GET /venues/prefill`, `POST /venues`, `GET /venues`, `GET /venues/{slug}`, `DELETE /venues/{slug}`
- `api/main.py` — added venues router, StaticFiles mount, four UI page routes
- `api/static/addvenue.html` — created; AI prefill, form, download-sources table, chip list
- `api/static/venues.html` — created; all-venues table with filter
- `api/static/conf.html` — created; conferences-only filtered table
- `api/static/journals.html` — created; journals-only filtered table
- `requirements.txt` — added `openai`, `aiofiles`
- `AGENTS.md` — updated §2 repo scope tree
- `CLAUDE.md` — updated syntax check command to include new modules
- `VERSION.md` — bumped to `paper-library-v0.1.6`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Venue data is stored as individual `<slug>.json` files (not MongoDB) so the store is portable, git-committable selectively, and requires no schema migration. Slug is derived from `short_name` (lowercase, non-word → underscore). LLM prefill is optional — if Azure credentials are absent, the endpoint returns `{"error": "prefill unavailable"}` without crashing. The `/venues/ui` path (not `/venues`) avoids a routing conflict with the `GET /venues` API endpoint registered on the same router prefix.

**Open items:** `ARCHITECTURE.md` should be updated to document the new venue endpoints and data flow in the next docs pass.

---

## [2026-05-27] claude-sonnet-4-6 — human-readable PDF filenames via RFR title slugger

**Action:** Added `POST /simplify-title` endpoint to RFR (`rfr/rag-system`) that uses Azure OpenAI to produce a 4–6 word snake_case slug from a full paper title. Added `venue` and `title_slug` fields to the `Paper` model. Replaced the SHA-256 filename scheme with a human-readable `{venue}_{year}__{title_slug}__{first_author_lastname}.pdf` builder that falls back gracefully when fields are missing. Updated ARCHITECTURE.md in both repos.

**Files changed (fastLibrary):**
- `services/models.py` — added `venue: str` and `title_slug: str` to `Paper` and `PaperUpdate`
- `api/routes/papers.py` — replaced `_doi_to_filename` with `_build_filename(doi, record)`; added `_slugify` helper; removed `hashlib`/`uuid4` filename dependency
- `ARCHITECTURE.md` — updated PDF upload flow, filename example, data contract table
- `VERSION.md` — bumped to `paper-library-v0.1.5`

**Files changed (rfr/rag-system):**
- `services/llm.py` — added `simplify_title()` function using existing Azure OpenAI client
- `api/main.py` — added `SimplifyTitleRequest` model and `POST /simplify-title` endpoint
- `ARCHITECTURE.md` — added `/simplify-title` to endpoint map with workflow description
- `VERSION.md` — bumped to `rag-system-v0.1.1`

**Decisions:** `title_slug` is caller-supplied (via RFR) rather than computed at upload time so paper-library has no dependency on RFR at runtime — the two services remain independently deployable. Fallback slug (first 5 words of title, lowercased) means the upload works even without RFR in the loop. Venue is a free-text field (e.g. `ICRA`, `TRO`) — not an enum — so callers control the short name.

**Open items:** The full PDF upload workflow is now: (1) POST metadata with `venue`/`authors`/`publication_year`, (2) call RFR `/simplify-title`, (3) PATCH `title_slug` onto the record, (4) POST PDF. This could be streamlined into a single import-and-slug step in `import_searcher.py`.

---

## [2026-05-27] codex-gpt-5 — verified issues 2 and 3 are resolved

**Action:** Validated that issue 2 (PDF upload memory pressure) and issue 3 (architecture validation model mismatch) are already fixed in the current branch. Confirmed chunked upload with in-stream size enforcement in `POST /papers/{doi:path}/pdf` and confirmed `ARCHITECTURE.md` now documents `UpsertRequest`/`BulkUpsertRequest` validation models.

**Files changed:**
- `AGENT_LOG.md` — prepended verification entry

**Decisions:** No further code changes were needed because both requested issues were already addressed by the latest implementation.

**Open items:** None for issues 2 and 3.

---

## [2026-05-27] codex-gpt-5 — made DOI-based PDF upload collision-safe and streamed

**Action:** Updated `POST /papers/{doi:path}/pdf` to stream uploads in 1 MB chunks (instead of reading entire file into memory), validate `%PDF` magic bytes on the first chunk, enforce the 200 MB limit during streaming, and write atomically via a temporary file. Replaced sanitizer-based filename mapping with deterministic `sha256(doi).pdf` so DOI identity maps consistently and avoids filename collisions between different DOIs.

**Files changed:**
- `api/routes/papers.py` — hash-based DOI filename helper, chunked upload handling, temp-file write/replace flow, empty-file validation
- `ARCHITECTURE.md` — updated validation model names and PDF upload flow to match streaming/hash behavior
- `VERSION.md` — bumped to `paper-library-v0.1.4`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Used SHA-256 over DOI as the filename to keep deterministic overwrite behavior per DOI while removing sanitizer collision risk. Used per-request temp filenames (`uuid4`) to avoid clobbering partial uploads when concurrent uploads happen.

**Open items:** No API contract change to endpoint path or response schema; clients can continue using existing upload calls.

---

## [2026-05-27] codex-gpt-5 — reviewed recent Claude changes from AGENT_LOG

**Action:** Audited the two newest Claude entries (`v0.1.2` upsert contract update and `v0.1.3` PDF upload endpoint) against current source files for behavioral risk, contract consistency, and documentation alignment.

**Files changed:**
- `AGENT_LOG.md` — prepended this review handoff entry

**Decisions:** Kept this as a review-only task with no code edits; focused findings on data integrity, resource usage risk, and log/doc consistency.

**Open items:** Review findings to address: DOI-to-filename collisions in PDF upload path can overwrite files across different records, upload path still reads full body into memory before size gate, and one architecture line still mentions only `Paper`/`PaperUpdate` validation despite `UpsertRequest`.

---

## [2026-05-27] claude-sonnet-4-6 — added PDF upload endpoint

**Action:** Added `POST /papers/{doi:path}/pdf` multipart upload endpoint. Metadata record must exist before upload (404 otherwise). Validates PDF magic bytes, enforces 200 MB limit, saves to `PDF_DIR/{sanitized_doi}.pdf`, updates `pdf_path` and `updated_at` on the record. Re-upload silently overwrites. Registered the `/pdf` route before the `/{doi:path}` catch-alls to avoid FastAPI routing ambiguity.

**Files changed:**
- `api/routes/papers.py` — added `upload_pdf` handler; added `_doi_to_filename` helper; reordered routes so fixed-path POST routes precede `/{doi:path}` catch-alls; added `re`, `Path`, `File`, `UploadFile` imports
- `requirements.txt` — added `python-multipart` (required by FastAPI for file uploads)
- `ARCHITECTURE.md` — added PDF upload path to request flow section; updated endpoint table; updated planned enhancements note
- `VERSION.md` — bumped to `paper-library-v0.1.3`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Read full file into memory before writing so we can validate magic bytes before touching the filesystem. 200 MB cap is generous for academic PDFs but prevents runaway uploads. DOI sanitization uses `re.sub(r"[^\w\-]", "_", doi)` — deterministic and reversible enough for a local store. Route ordering comment added in code to warn future agents not to reorder.

**Open items:** Large PDFs (>50 MB) will hold the request in memory; a streaming write with magic-byte check on the first chunk would be more efficient if very large files become common.

---

## [2026-05-27] claude-sonnet-4-6 — reviewed codex changes, fixed POST /papers body contract

**Action:** Reviewed all codex-gpt-5 changes from v0.1.1. Found one API inconsistency: `overwrite_missing_fields` on `POST /papers` was a query param while the same flag on `POST /papers/bulk` was a body field. Fixed by introducing `UpsertRequest` wrapper model so both endpoints keep the flag in the body. Documented sparse-upsert semantics (`exclude_unset=True` behavior) explicitly in `ARCHITECTURE.md`.

**Files changed:**
- `services/models.py` — added `UpsertRequest` wrapper model (`paper` + `overwrite_missing_fields`)
- `api/routes/papers.py` — `POST /papers` now accepts `UpsertRequest` body instead of `Paper` + query param
- `ARCHITECTURE.md` — updated endpoint table for `POST /papers`; expanded overwrite semantics section with `exclude_unset` explanation
- `VERSION.md` — bumped to `paper-library-v0.1.2`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Used a wrapper model rather than promoting the flag to a query param on both endpoints, because the body-based pattern is more consistent with REST conventions for non-idempotent operations and keeps the request self-describing.

**Open items:** All prior open items from codex review pass. No new open items.

---

## [2026-05-27] codex-gpt-5 — fixed sparse-upsert safety and overwrite flags

**Action:** Implemented the requested overwrite controls. Default upsert behavior now preserves existing fields when payload fields are omitted. Added explicit flags to overwrite missing fields and to resolve duplicate DOI rows in bulk payloads. Added DOI non-empty validation, improved bulk-write error reporting, enforced MongoDB localhost bind in deployment, and updated architecture/version docs.

**Files changed:**
- `services/models.py` — DOI validation + bulk overwrite flags + safe list defaults
- `services/mongo.py` — sparse-vs-overwrite upsert logic, duplicate DOI handling, bulk write error handling
- `api/routes/papers.py` — `overwrite_missing_fields` support on single upsert and bulk flag plumbing
- `scripts/import_searcher.py` — CLI flags for overwrite behavior
- `deploy/proxmox_deploy.sh` — explicit localhost bind enforcement and bind verification for mongod
- `ARCHITECTURE.md` — updated endpoint contracts and overwrite behavior docs
- `VERSION.md` — bumped to `paper-library-v0.1.1`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Used request-level explicit flags (`overwrite_missing_fields`, `overwrite_duplicate_doi`) so existing clients keep safe defaults without breaking changes. For duplicate DOI overwrite mode, the last payload row is retained per DOI.

**Open items:** Existing deployed LXCs should be refreshed or manually updated if they were provisioned before localhost bind enforcement in `deploy/proxmox_deploy.sh`.

---

## [2026-05-27] codex-gpt-5 — performed repository code review

**Action:** Reviewed API, data layer, models, scripts, and deploy automation for behavioral regressions and policy alignment. Focused on idempotency, DOI handling, and MongoDB exposure guarantees.

**Files changed:**
- `AGENT_LOG.md` — prepended this review handoff entry

**Decisions:** Did not modify application code because the request was review-only; reported findings with severity and concrete file/line references for follow-up fixes.

**Open items:** Address review findings: sparse upserts can wipe existing fields, DOI is not constrained as non-empty at API boundary, duplicate DOI rows in one bulk request can trigger bulk write failures, and deploy script does not explicitly enforce MongoDB localhost binding.

---

## [2026-05-27] claude-sonnet-4-6 — added agent handoff log protocol

**Action:** Added `AGENT_LOG.md` handoff protocol to both `CLAUDE.md` (§6) and `AGENTS.md` (§10) so that every agent — Claude, Codex, or other — reads this file before acting and prepends an entry after acting. Created this file as the initial log.

**Files changed:**
- `CLAUDE.md` — added §6 Agent Handoff Log
- `AGENTS.md` — added §10 Agent Handoff Log, renumbered Change Workflow to §11
- `AGENT_LOG.md` — created (this file)

**Decisions:** Newest-first ordering keeps the most relevant context at the top of the file without requiring a full read. Archive threshold of 200 lines / 10 entries keeps the active file small enough to fit in any agent's context window cheaply.

**Open items:** None from this change. See `history/2026-05.md` for the initial scaffold entry.

---
