# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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
