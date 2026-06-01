# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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

## [2026-06-01] codex-gpt-5 — restore papers API backward compatibility and isolate UI route

**Action:** Reviewed the most recent Claude change that introduced `papers.html` and moved the papers API to `/api/papers`. Implemented a compatibility fix to preserve existing `/papers` API clients while keeping the new browser page. `api/main.py` now mounts the papers router at both `/papers` (legacy/default) and `/api/papers` (alias), and moves the HTML page route to `GET /papers-ui` to avoid path collisions. Updated all navigation links to point to `/papers-ui`, updated architecture docs with the dual-prefix API note and missing UI routes, and ran syntax checks.

**Files changed:**
- `api/main.py` — mounted papers router on `/papers` and `/api/papers`; moved page route `/papers` → `/papers-ui`
- `api/static/conf.html`, `venues.html`, `journals.html`, `venue.html`, `addconf.html`, `addjournal.html`, `strategies.html`, `papers.html` — navigation links updated to `/papers-ui`
- `ARCHITECTURE.md` — documented dual papers API prefixes and added missing UI routes
- `VERSION.md` — bumped to `paper-library-v0.1.82`
- `AGENT_LOG.md` — prepended this entry and archived entries beyond 10 most recent
- `history/2026-05.md` — received archived AGENT_LOG entries

**Decisions:** Kept `/api/papers` as a first-class alias so the new UI remains unchanged, while restoring `/papers` for backwards compatibility with existing API clients and scripts.

**Open items:** Existing bookmarks to `/papers` (HTML page path from the Claude change) should switch to `/papers-ui`; `/papers` is now reserved for JSON API responses.

---

## [2026-06-01] claude-sonnet-4-6 — add /papers page with search, filters, and detail panel

**Action:** Created `api/static/papers.html` — a paginated, searchable list of all papers backed by `GET /api/papers`. Filters: title (full-text), year range, downloaded status, tags. Columns: Paper (title + authors + DOI), Tags, Year, Venue, Downloaded. Clicking a title opens a detail panel showing all fields including BibTeX with a copy button. Added `GET /papers` page route to `main.py`. Moved papers API prefix from `/papers` to `/api/papers` so the page URL `/papers` is unambiguous; updated `scripts/import_searcher.py` to use the new prefix. Added Papers nav link to all existing pages.

**Files changed:**
- `api/static/papers.html` — new papers listing page
- `api/main.py` — `/papers` page route added; papers API prefix changed to `/api/papers`
- `scripts/import_searcher.py` — bulk URL updated to `/api/papers/bulk`
- `api/static/conf.html`, `venues.html`, `journals.html`, `venue.html`, `addconf.html`, `addjournal.html`, `tags.html`, `strategies.html` — Papers nav link added
- `VERSION.md` — bumped to `paper-library-v0.1.81`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** API moved to `/api/papers` to match the pattern used by venues and strategies. Client-side sort on top of paginated results since the API doesn't support server-side ordering. `venue_long` preferred over `venue` in the Venue column. Detail panel shows BibTeX inline with clipboard copy button.

**Open items:** `/papers` prefix change is breaking for any external client using the old prefix.

---

## [2026-06-01] claude-sonnet-4-6 — fix cancelled status persisted as error in venue JSON

**Action:** Reviewed codex's cancel-race and pdf_error fixes — both correct and kept as-is. Fixed the one remaining issue codex flagged as an open item: `_persist_download_stats` was mapping all non-empty error strings to `last_status: "error"`, so cancelled downloads showed as errors in the venue JSON and on the UI status column. Added `"cancelled"` as a recognised value in `_normalize_download_stats` (previously stripped to `""`), added it to `_persist_download_stats` detection logic, and added a `status-cancelled` CSS class (grey) to `venue.html` so it renders distinctly from both success and error.

**Files changed:**
- `api/routes/venues.py` — `_normalize_download_stats` accepts `"cancelled"`; `_persist_download_stats` sets `last_status: "cancelled"` when error is `"cancelled by user"`
- `api/static/venue.html` — `renderPapers` maps `"cancelled"` to `status-cancelled` class; CSS `.status-cancelled` added (grey)
- `VERSION.md` — bumped to `paper-library-v0.1.80`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `"cancelled by user"` string comparison is intentional — it's the only string passed by the two cancel paths in `_run_download_task`. Avoids adding a new enum or constant for a single call site.

**Open items:** None.

---

