# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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

## [2026-06-01] claude-sonnet-4-6 — add PDF view/download icons to papers page

**Action:** Added a new actions column (eyeglass 🔍 / download ⬇ icons) to the left of Paper information on the papers page. Clicking 🔍 opens the stored PDF inline in a new tab; clicking ⬇ triggers a browser file download. Icons are disabled (greyed out) when no PDF is stored. Added `GET /api/papers/{doi:path}/pdf` endpoint to `papers.py` that serves the file from `pdf_path` with `Content-Disposition: inline` (view) or `attachment` (download) based on a `?download=true` query param. Removed the clickable link styling from the paper title.

**Files changed:**
- `api/routes/papers.py` — added `GET /{doi:path}/pdf` endpoint with `FileResponse`; imported `FileResponse`
- `api/static/papers.html` — actions column with icon buttons; `viewPdf`, `downloadPdf`, `_pdfUrl` helpers; removed paper-title link styling
- `VERSION.md` — bumped to `paper-library-v0.1.87`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** DOI path segments are individually percent-encoded then joined with `/` so DOIs like `10.0000/atrd_symposium.2025.foo` survive URL parsing correctly. View uses `window.open` (new tab); download uses a hidden `<a download>` click to trigger the browser save dialog without navigation.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — fix paper detail panel not opening on click

**Action:** `openDetail` was called with `JSON.stringify(JSON.stringify(p))` embedded in the `onclick` HTML attribute. This broke in two ways: (1) only one `JSON.parse` call unwrapped the double-encoded string, leaving a string instead of an object; (2) paper titles and fields containing quotes, `<`, `>`, or `&` corrupted the HTML attribute. Fixed by storing rendered papers in a module-level `_paperCache` map (index → object), passing only the integer index to `onclick="openDetail(idx)"`, and looking up the paper object in the handler. Cache is cleared on each `render()` call.

**Files changed:**
- `api/static/papers.html` — `_paperCache` map; `render()` populates cache and uses index in onclick; `openDetail(idx)` looks up from cache
- `VERSION.md` — bumped to `paper-library-v0.1.86`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Index-based lookup is the standard pattern for passing complex objects through HTML event attributes — avoids all serialisation/escaping issues entirely.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — parallel PDF downloads for ATRD via concurrency strategy config

**Action:** Added parallel PDF download support controlled by `concurrency` in the strategy's `download_pdf` step config. Added `_apply_download_pdfs_parallel` — an async function that dispatches all PDF downloads concurrently using `asyncio.gather` with an `asyncio.Semaphore` to cap simultaneous requests. An `on_progress` callback fires after each paper completes so the task counter updates in real time. `_run_download_task` now detects `concurrency > 1` and takes a parallel path: phase 1 applies all pre-download steps (generate_doi) to the full batch; phase 2 runs parallel downloads; phase 3 applies post-download steps (build_bibtex, upsert_papers) sequentially. The sequential path (concurrency ≤ 1) is preserved unchanged. Set `concurrency: 5` in `strategies/atrd.json`.

**Files changed:**
- `api/routes/venues.py` — `_apply_download_pdfs_parallel` with semaphore and progress callback; `_run_download_task` parallel/sequential branching
- `strategies/atrd.json` — `concurrency: 5` added to `download_pdf` step config
- `VERSION.md` — bumped to `paper-library-v0.1.85`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Concurrency of 5 is conservative — Google Drive can throttle; raise if the searcher handles it well. Cancel checks remain between phases so a cancel mid-download is still honoured. Progress counter in the parallel path increments as each PDF finishes, so the UI "Downloading X/Y" stays live even with batch execution.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — fix 500 on download start caused by missing tasks/ directory

**Action:** Download start was returning plain-text "Internal Server Error" because `_write_task` was calling `TASKS_DIR.mkdir` on a directory that didn't exist on the deployed server (the deploy scripts were updated but `update.sh` hadn't been run yet). The OSError propagated unhandled out of `start_download` as a non-JSON 500. Fixed by: (1) creating all runtime directories (`PDF_DIR`, `VENUES_DIR`, `STRATEGIES_DIR`, `TASKS_DIR`) in the app lifespan on startup — server now self-heals on restart; (2) wrapping `_write_task` to re-raise as `RuntimeError`; (3) catching that in `start_download` and raising `HTTPException(500)` so the client always gets JSON.

**Files changed:**
- `api/main.py` — lifespan creates all runtime dirs on startup
- `api/routes/venues.py` — `_write_task` wraps filesystem errors; `start_download` catches and raises HTTP 500
- `VERSION.md` — bumped to `paper-library-v0.1.84`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Lifespan directory creation is idempotent (`exist_ok=True`) so it's safe on every restart. This also fixes any future case where `venues/`, `pdf/`, or `strategies/` are missing without requiring a manual deploy step.

**Open items:** The deployed server still needs a service restart to trigger the lifespan and create `tasks/`. Run `sudo systemctl restart paper-library` on the LXC, then retry the download.

---

## [2026-06-01] claude-sonnet-4-6 — fix missing Papers nav link in tags.html; clean up router order

**Action:** Reviewed codex's `/papers-ui` backward-compat change. The approach is correct — dual-mounting the router at `/papers` (legacy) and `/api/papers` (canonical) cleanly resolves the URL conflict. Found one miss: `tags.html` was not included in codex's sed pass and was missing the Papers nav link. Fixed. Also reordered router registrations in `main.py` so `health` comes first and the legacy `/papers` alias is clearly annotated, matching the pattern used by other routers.

**Files changed:**
- `api/static/tags.html` — added `<a href="/papers-ui">Papers</a>` nav link
- `api/main.py` — reordered routers: health first, then `/api/papers`, then `/papers` legacy alias with comment
- `VERSION.md` — bumped to `paper-library-v0.1.83`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** No functional change — all routes and prefixes remain the same. Router order change is cosmetic only; FastAPI registration order only matters for path conflicts, which don't exist here.

**Open items:** None.

---

