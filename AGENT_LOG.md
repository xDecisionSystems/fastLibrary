# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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

## [2026-06-01] codex-gpt-5 — fix async download cancel race and surface PDF step errors

**Action:** Reviewed the latest Claude async-download changes and fixed two regressions in task execution. First, cancel requests could be overwritten by the worker loop (`running` status rewrites), making cancel effectively unreliable mid-paper; added cancellation checks both before and after per-paper step execution, preserving cancelled state and persisting partial stats. Second, `download_pdf` failures were stored only as transient `pdf_error` fields and never surfaced in task/error status; now these per-paper failures are appended to task errors so final status can correctly become `partial/error` instead of silent `success`. Also updated `ARCHITECTURE.md` to document async `/start|/status|/cancel` endpoints and `tasks/` task-state files.

**Files changed:**
- `api/routes/venues.py` — robust cancel handling in `_run_download_task`; per-paper `pdf_error` propagation into task errors
- `ARCHITECTURE.md` — documented async download endpoints, task status model, and `TASKS_DIR` runtime path constant
- `VERSION.md` — bumped to `paper-library-v0.1.79`
- `AGENT_LOG.md` — prepended this entry and archived older entries
- `history/2026-05.md` — received archived AGENT_LOG entries beyond 10 most recent

**Decisions:** Cancellation is treated as a first-class terminal state that preserves already-completed progress (`downloaded` count) and writes `paper_downloads` with `last_status=error` and `last_error="cancelled by user"` to keep behavior compatible with existing status schema.

**Open items:** Consider adding a distinct `cancelled` value to persisted `paper_downloads.last_status` in a future schema update to avoid overloading `error` for user-initiated stops.

---

## [2026-06-01] claude-sonnet-4-6 — fix step order in atrd strategy and wire upsert_papers step

**Action:** Fixed two issues in the ATRD download strategy. (1) Step order was wrong — `download_pdf` ran before `generate_doi`, so papers had no DOI when the PDF filename was derived and when they were upserted. Corrected order: `fetch_papers` → `generate_doi` → `download_pdf` → `build_bibtex` → `upsert_papers`. (2) The `upsert_papers` step inherited from `_default` was never executed — the upsert was hardcoded outside the step loop. Added `bulk_upsert` step type handling in `_run_download_task`: when the strategy declares `upsert_papers`, the loop executes it as part of the step chain and sets `upsert_after_steps=False` to suppress the fallback hardcoded upsert. Strategies without a `bulk_upsert` step fall back to the hardcoded upsert so existing behavior is preserved.

**Files changed:**
- `strategies/atrd.json` — corrected step order; added explicit `upsert_papers` step
- `api/routes/venues.py` — `_run_download_task` handles `bulk_upsert` step type; `upsert_after_steps` flag suppresses fallback when strategy declares its own upsert
- `VERSION.md` — bumped to `paper-library-v0.1.78`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `upsert_after_steps` fallback ensures strategies that don't declare `upsert_papers` (e.g. venues with no strategy) still upsert papers. Per-paper upsert inside the step loop means the record is written to MongoDB immediately after its PDF is downloaded and BibTeX is built — no batching delay.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — async per-paper download with live progress and cancel

**Action:** Replaced the single blocking download call with an async background task system. Three new endpoints: `POST /{slug}/paper-downloads/{year}/start` launches a background task and returns immediately; `GET /{slug}/paper-downloads/{year}/status` returns current progress; `POST /{slug}/paper-downloads/{year}/cancel` signals the running task to stop. Task state is persisted to `tasks/<slug>-<year>.json` so progress survives page navigation and server restarts. The background task iterates papers one at a time, running strategy steps (generate_doi, download_pdf, build_bibtex) and upserting each paper individually, writing updated counts after every paper. Added `TASKS_DIR = Path("tasks")` to config. The venue page polls `/status` every 2 seconds while a download is running, updates the Downloaded count cell live, shows "Downloading X/Y…" inline, and replaces the Download button with a Cancel button. On page load, any year with a running task automatically resumes polling.

**Files changed:**
- `config/settings.py` — added `TASKS_DIR`
- `api/routes/venues.py` — added `BackgroundTasks` import; `_task_path`, `_read_task`, `_write_task`, `_task_running`, `_persist_download_stats`, `_run_download_task` helpers; `start_download`, `get_download_status`, `cancel_download` endpoints
- `api/static/venue.html` — `_pollTimers` map; `_actionsCell`, `_applyTaskToRow`, `_startPolling` helpers; updated `downloadYear` to use `/start`; added `cancelDownload`; `loadPapers` resumes polling on page load
- `VERSION.md` — bumped to `paper-library-v0.1.77`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Task state is file-based (not in-memory) so it persists across restarts and is readable by any future agent or tool. Cancel is cooperative — the task checks for `"cancelled"` status between each paper. The old `POST /{slug}/paper-downloads/{year}` endpoint is kept as-is for backward compatibility (scripts/CLI use).

**Open items:** `tasks/` directory should be added to `.gitignore` and created on deploy. Task files are never cleaned up — a future maintenance step could prune files older than N days.

---

## [2026-05-31] codex-gpt-5 — implement post-review fixes for BibTeX, strategy auto-selection, and docs
**Action:** Implemented the requested fixes from the post-review findings. Hardened BibTeX generation so blank/whitespace-only author entries no longer crash cite-key creation. Improved BibTeX completeness by backfilling `venue_long`, `venue`, and `publication_year` from venue/year context before entry generation. Expanded default strategy auto-selection from exact-file match to include strategy `aliases`, unique prefix matches, and unique token-subset matches, while preserving deterministic/empty fallback behavior when ambiguous. Synced `ARCHITECTURE.md` with current contracts (searcher default base path, new paper fields, merged venue/getpapers UX).  
**Files changed:** `api/routes/venues.py`, `ARCHITECTURE.md`, `VERSION.md`, `AGENT_LOG.md`  
**Decisions:** Kept strategy auto-selection conservative: it only auto-maps when a single best match exists (alias, prefix, or highest token-subset score). Ambiguous matches still return blank strategy to avoid surprising routing.  
**Open items:** Strategy aliases are optional metadata and are only used when present in strategy JSON files; if future workflows rely on aliases heavily, validate/persist alias fields in the strategy CRUD model/API.

---

## [2026-05-31] codex-gpt-5 — review post-codex Claude changes and flag regressions

**Action:** Reviewed all AGENT_LOG entries added after the last Codex edit, inspected corresponding code paths (venue route/search/download flow, merged venue UI papers section, strategy files, models, and app routes), and identified functional/doc/process regressions needing follow-up.

**Files changed:**
- `AGENT_LOG.md` — prepended this review handoff and kept 10 most recent entries per policy
- `history/2026-05.md` — appended older AGENT_LOG entries during archive rollup

**Decisions:** Review-only pass; no runtime code edits were applied in this step.

**Open items:** Fix needed for BibTeX robustness/completeness (`_build_bibtex_entry` blank-author crash and missing venue_long fallback), plus architecture/log policy drift corrections.

---

## [2026-05-31] claude-sonnet-4-6 — merge getpapers into venue page; remove /getpapers route

**Action:** Merged the full paper download/search section from `getpapers.html` into `venue.html`. The Papers section (year table, Search/Download buttons, search modal) now appears below the edit form on conference venue pages and is hidden for journals. `venue.html` also gains Location and Month columns in the Per-Year Proceedings table (mapping to new `DownloadSource.location` and `.month` fields). `/getpapers/<slug>` now 301-redirects to `/venues/<slug>`. All listing pages (conf.html, venues.html) updated: name links and action buttons all point to `/venues/<slug>`; the separate "Get Papers" button is removed.

**Files changed:**
- `api/static/venue.html` — merged papers section; Location/Month in sources table; removed `getpapers-link`
- `api/static/conf.html` — name links and actions → `/venues/<slug>`; "Get Papers" button removed
- `api/static/venues.html` — name links and actions → `/venues/<slug>`; "Get Papers" button removed
- `api/main.py` — `/getpapers/{slug}` now 301-redirects to `/venues/{slug}`
- `VERSION.md` — bumped to `paper-library-v0.1.75`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `getpapers.html` is kept on disk but no longer served — the redirect handles any bookmarked or linked URLs. Papers section visibility is toggled by `onTypeChange()` so it only appears when `type === "conference"`. `loadPapers()` is called automatically when `populate()` detects a conference type.

**Open items:** `getpapers.html` can be deleted in a future cleanup once the redirect has been live long enough.

---

## [2026-05-31] claude-sonnet-4-6 — clickable names on venue listing pages

**Action:** Short name and long name columns on all three venue listing pages are now clickable links. Conferences (conf.html and the All venues page) link to `/getpapers/<slug>`. Journals (journals.html and the All venues page) link to `/venues/<slug>`. Links use `color:inherit` so they blend with existing text styling and show underline only on hover.

**Files changed:**
- `api/static/conf.html` — short_name and long_name wrapped in `/getpapers/` links
- `api/static/journals.html` — short_name and long_name wrapped in `/venues/` links
- `api/static/venues.html` — short_name and long_name wrapped in type-conditional links (`/getpapers/` for conferences, `/venues/` for journals)
- `VERSION.md` — bumped to `paper-library-v0.1.74`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Conferences link to getpapers (the primary action for a conference) rather than the venue edit page, since the View button already covers that. Journals have no getpapers page so they link to the venue detail/edit page.

**Open items:** None.

---

