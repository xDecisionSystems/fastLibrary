# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

---

## [2026-06-01] codex-gpt-5 — review latest Claude filename/bulk-download changes; prevent PDF overwrite collisions

**Action:** Reviewed the newest Claude entries (`v0.1.93`–`v0.1.96`) covering LLM PDF filenames and venue-level Search All/Download All controls. Applied follow-up fixes where needed. In `download_pdf`, LLM-generated names could collide and silently overwrite files (especially in parallel mode); added deterministic destination reservation with collision-resistant suffixing and pre-planned per-paper paths so parallel writes cannot race onto the same filename. Also serialized filename planning in the parallel path (instead of unbounded per-paper LLM calls), added a missing `chat_deployment_name` guard in `generate_pdf_filename`, fixed cancelled-status styling in live task polling (`status-cancelled` instead of error red), and updated `ARCHITECTURE.md` to document filename generation + de-dup behavior.

**Files changed:**
- `api/routes/venues.py` — added filename identity and destination reservation helpers; applied deterministic de-dup in sequential and parallel PDF download paths
- `services/venues.py` — `generate_pdf_filename` now requires configured `chat_deployment_name` before calling Azure OpenAI
- `api/static/venue.html` — `_applyTaskToRow` now maps `cancelled` to `status-cancelled`
- `ARCHITECTURE.md` — documented LLM filename generation and batch de-dup guarantees
- `VERSION.md` — bumped to `paper-library-v0.1.97`
- `AGENT_LOG.md` — prepended this entry and archived entries beyond 10 most recent
- `history/2026-06.md` — received archived AGENT_LOG entries

**Decisions:** Kept filename format behavior intact while adding deterministic disambiguation only when collisions occur, preserving human-readable names but preventing data loss from overwrite races.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — add Search All and Download All buttons to conference venue page

**Action:** Added "Search All" and "Download All" buttons to the Papers section of the conference venue page. Search All runs `POST /paper-search/{year}` sequentially for every year where `found_papers` is null (never searched), updating the Found cell live as each completes. Download All calls `downloadYear()` for every year where `downloaded_papers === 0` and `last_status !== 'success'` and no task is already running, with a 500ms gap between starts; existing polling handles live progress per year. Both buttons are disabled during execution and re-enabled when done.

**Files changed:**
- `api/static/venue.html` — Search All and Download All buttons in controls bar; `searchAll()` and `downloadAll()` functions
- `VERSION.md` — bumped to `paper-library-v0.1.96`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Sequential execution for Search All (one year at a time, awaited) prevents hammering the searcher. Download All starts tasks back-to-back with a 500ms gap — each year runs as an independent background task on the server so they proceed in parallel server-side while the UI polls each independently.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — improve PDF filename prompt to prefer distinctive technical terms

**Action:** The previous prompt was choosing leading/generic words from titles (e.g. "procedural_terminal_area_airspace_integration" instead of "procedures_uncrewed_aircraft_untowered_airports"). Updated `_PDF_FILENAME_PROMPT` to explicitly instruct the model to pick the most specific and distinctive nouns/adjectives, avoid generic words (concept, approach, system, integration, analysis), and prefer domain-specific technical terms. Added a concrete example using the target paper. Capped simple_title at 3-5 words (was 3-6).

**Files changed:**
- `services/venues.py` — updated `_PDF_FILENAME_PROMPT` with stronger specificity guidance and example
- `VERSION.md` — bumped to `paper-library-v0.1.95`
- `AGENT_LOG.md` — prepended this entry

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — PDF filename format: underscores within fields, dashes between fields

**Action:** Updated `_PDF_FILENAME_PROMPT` to specify underscores within each field and dashes between fields. Format is now `<simple_title>-<first_author_lastname>-<venue_short>-<year>.pdf`. Example: `evaluation_utm_conops_drone-li-atrd-2025.pdf`. Updated the validation regex from `[a-z0-9\-]*` to `[a-z0-9_\-]*` to accept underscores.

**Files changed:**
- `services/venues.py` — updated prompt rules and example; regex allows underscores
- `VERSION.md` — bumped to `paper-library-v0.1.94`
- `AGENT_LOG.md` — prepended this entry

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — LLM-generated PDF filenames via Azure OpenAI

**Action:** Added `generate_pdf_filename(title, authors, venue, year)` to `services/venues.py`. Calls Azure OpenAI with a prompt requesting format `<3-6-word-title>-<first-author>-<venue>-<year>.pdf` using lowercase words and hyphens only. Response is validated against `[a-z0-9][a-z0-9\-]*\.pdf` before use. Added `_pdf_filename_for_paper(paper, venue_doc, year)` helper in `venues.py` that calls the LLM and falls back to the slug-based name if credentials are missing or the call fails. Both `_apply_download_pdfs` (sequential) and `_apply_download_pdfs_parallel` (parallel, via `asyncio.to_thread`) now use this helper.

Example output: `evaluation-utm-conops-drone-deliveries-li-atrd-2025.pdf`

**Files changed:**
- `services/venues.py` — added `_PDF_FILENAME_PROMPT` and `generate_pdf_filename`
- `api/routes/venues.py` — imported `generate_pdf_filename`; added `_pdf_filename_for_paper`; updated both download functions to use it
- `VERSION.md` — bumped to `paper-library-v0.1.93`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** LLM call is synchronous (wrapped in `asyncio.to_thread` for the parallel path). Fallback to slug ensures downloads never fail because of an LLM error. Response validation rejects anything that doesn't match the safe filename pattern so a runaway LLM response can't write to an arbitrary path.

**Open items:** Each parallel PDF download now makes an additional LLM call, so 53 ATRD papers = 53 LLM calls. These are cheap (64 tokens each) but worth monitoring if the batch size grows. Could be batched in a pre-pass if latency becomes an issue.

---

## [2026-06-01] codex-gpt-5 — review latest Claude admin changes; fix task-state reset and docs drift

**Action:** Reviewed the latest Claude changes (`v0.1.90` ingested inference and `v0.1.91` admin wipe flow). Confirmed `_to_paper_model` now marks papers ingested when `pdf_path` is present. Applied follow-up fixes around the new admin reset path: added task-state file cleanup (`tasks/*.json`) to prevent stale download status after a full wipe, hardened admin UI error rendering with HTML escaping, and synced `ARCHITECTURE.md` with newly added endpoints/routes (`GET /papers/{doi:path}/pdf`, `POST /api/admin/delete-all-papers`, `/admin` page route).

**Files changed:**
- `api/routes/admin.py` — removed unused imports; delete persisted task-state JSON files; include `deleted_task_states` in response
- `api/static/admin.html` — added escaping helper for rendered errors; show deleted task-state count in results
- `ARCHITECTURE.md` — documented stored-PDF GET endpoint, admin API endpoint, and `/admin` UI route
- `VERSION.md` — bumped to `paper-library-v0.1.92`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Kept admin endpoint semantics additive (no breaking contract changes): task-state cleanup is included in the same operation and returned as an additional count field.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — add admin page with delete-all-papers action

**Action:** Added an Admin page at `/admin` with a single destructive action: Delete All Papers. The action deletes all paper records from MongoDB, clears the `paper_search_cache` collection, removes all `.pdf` files from `PDF_DIR`, and resets `paper_downloads` to `{}` on every venue JSON file. A confirmation dialog is shown before execution. The result panel shows counts for each operation. Added `POST /api/admin/delete-all-papers` endpoint in a new `api/routes/admin.py` router. Added `delete_all_papers` and `clear_search_cache` helpers to `services/mongo.py`. Registered the admin router at `/api/admin` in `main.py` and added Admin nav link to all pages.

**Files changed:**
- `api/routes/admin.py` — new admin router with `delete-all-papers` endpoint
- `services/mongo.py` — added `delete_all_papers`, `clear_search_cache` helpers
- `api/main.py` — registered admin router; added `/admin` page route
- `api/static/admin.html` — new admin page
- `api/static/{conf,venues,journals,venue,addconf,addjournal,papers,tags,strategies}.html` — Admin nav link added
- `VERSION.md` — bumped to `paper-library-v0.1.91`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** PDF deletion walks `PDF_DIR.rglob("*.pdf")` so it catches files in any subdirectory. Venue `paper_downloads` is reset to `{}` rather than deleted so the year entries reappear when the venue is re-saved. Errors are collected per operation and returned in the response rather than aborting early.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — mark paper ingested=True when pdf_path is set

**Action:** ATRD papers were being upserted with `ingested=False` because `_to_paper_model` defaulted to `raw.get("ingested", False)` and the ATRD searcher response never includes an `ingested` field. Papers with a stored PDF are by definition ingested. Fixed by treating a non-empty `pdf_path` as implicit evidence of ingestion: `ingested=bool(raw.get("ingested") or pdf_path)`.

**Files changed:**
- `api/routes/venues.py` — `_to_paper_model` sets `ingested=True` when `pdf_path` is present
- `VERSION.md` — bumped to `paper-library-v0.1.90`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Preserves explicit `ingested=True` from any source that sets it directly. Papers without a PDF that explicitly set `ingested=True` (e.g. via the API) are also preserved. Only the missing-field default case is changed.

**Open items:** Already-downloaded ATRD papers in the database have `ingested=False` — they won't be corrected until re-downloaded or manually patched. A one-time MongoDB update would fix existing records: `db.papers.updateMany({pdf_path: {$exists: true, $ne: ""}}, {$set: {ingested: true}})`.

---

## [2026-06-01] codex-gpt-5 — fix papers detail access regression and secure PDF file serving

**Action:** Reviewed the most recent Claude changes (v0.1.83–v0.1.88) and fixed two regressions. First, the papers detail panel became unreachable after icon-column updates because `openDetail()` was no longer called anywhere in the rendered rows; restored detail access by wiring title click to `openDetail(idx)` and adding hover/cursor affordance. Second, the new `GET /api/papers/{doi}/pdf` endpoint trusted `pdf_path` from metadata and could serve files outside the project PDF directory if a record was poisoned; added path canonicalization and `PDF_DIR` boundary enforcement before serving.

**Files changed:**
- `api/routes/papers.py` — enforced `pdf_path` resolution inside `PDF_DIR` in `serve_pdf`
- `api/static/papers.html` — restored `openDetail(idx)` click path on paper title; added pointer/hover affordance
- `VERSION.md` — bumped to `paper-library-v0.1.89`
- `AGENT_LOG.md` — prepended this entry and archived older entries beyond 10 most recent
- `history/2026-06.md` — received archived AGENT_LOG entries

**Decisions:** Rejected out-of-root `pdf_path` values with HTTP 400 rather than silently normalizing to prevent accidental or malicious file disclosure through metadata writes.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — rename PDF Link to External PDF Link; add server PDF Link in detail panel

**Action:** In the paper detail panel, renamed `"PDF Link"` (the original `pdf_link` field from the searcher) to `"External PDF Link"`. Added a new `"PDF Link"` row that shows the filename as a clickable link to the locally stored PDF via `GET /api/papers/{doi}/pdf` — only shown when `pdf_path` is set.

**Files changed:**
- `api/static/papers.html` — detail panel: `pdf_link` row label → `"External PDF Link"`; new `"PDF Link"` row linking to `/api/papers/{doi}/pdf`
- `VERSION.md` — bumped to `paper-library-v0.1.88`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Used `_pdfUrl(idx, false)` (already in scope inside `openDetail`) to build the server PDF URL, keeping the same DOI encoding logic as the icon buttons.

**Open items:** None.

---

