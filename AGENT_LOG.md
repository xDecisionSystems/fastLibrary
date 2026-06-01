# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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

## [2026-05-31] claude-sonnet-4-6 — add build_bibtex strategy step for @inproceedings generation

**Action:** Added a `build_bibtex` strategy step type that assembles a complete `@inproceedings` BibTeX entry for each paper. Added `location` and `month` fields to `DownloadSource` so per-year venue city and month can be stored alongside the URL. Added `bibtex: str` field to `Paper` and `PaperUpdate`. Implemented `_build_bibtex_entry` and `_apply_build_bibtex` in venues.py — reads `location`/`month` from the matching `download_sources` entry, uses `venue_long` as `booktitle`, adds a `note` field when `doi_synthetic=true`. Wired into `_search_papers_for_venue` step loop. Added `build_bibtex` as the final step in `strategies/atrd.json`. `bibtex` passed through `_to_paper_model` and stored in MongoDB.

**Files changed:**
- `services/models.py` — `DownloadSource` gains `location` and `month`; `Paper`/`PaperUpdate` gain `bibtex`
- `api/routes/venues.py` — `_build_bibtex_entry`, `_apply_build_bibtex` helpers; `build_bibtex` wired in step loop; `bibtex` in `_to_paper_model`
- `strategies/atrd.json` — `build_bibtex` step added as final step
- `VERSION.md` — bumped to `paper-library-v0.1.73`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `build_bibtex` runs on both Search and Download (no `download_pdfs` gate needed — it's pure data assembly). Cite key is `<first_author_lastname><year>` (e.g. `li2025`). Fields are omitted when empty so partial data still produces valid BibTeX. `address` and `month` come from `download_sources[year].location` and `.month` — the ATRD 2025 entry on the server needs those fields populated (`Prague, Czech Republic` / `June`).

**Open items:** The ATRD Symposium venue on the server needs its 2025 `download_sources` entry updated with `location: "Prague, Czech Republic"` and `month: "June"` to get fully populated BibTeX entries.

---

## [2026-05-31] claude-sonnet-4-6 — add venue_long, is_best_paper, presentation_url to Paper model

**Action:** Added three fields to `Paper` and `PaperUpdate` models to cover missing BibTeX and ATRD-specific data. `venue_long` stores the full proceedings/journal title (used as `booktitle` in BibTeX) populated from `venue_doc["long_name"]`. `is_best_paper` and `presentation_url` capture ATRD-specific metadata previously dropped in `_to_paper_model`. Updated `_to_paper_model` to map all three from the raw candidate and venue doc.

**Files changed:**
- `services/models.py` — added `venue_long`, `is_best_paper`, `presentation_url` to `Paper` and `PaperUpdate`
- `api/routes/venues.py` — `_to_paper_model` maps `venue_long` from `venue_doc["long_name"]`, `is_best_paper` and `presentation_url` from raw candidate
- `VERSION.md` — bumped to `paper-library-v0.1.72`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `venue_long` falls back to `raw.get("venue_long")` first so it can be overridden by the searcher if it ever returns it, then `venue_doc["long_name"]`. For ATRD the long name is `"U.S./Europe Air Transportation Research and Development Seminar"` which is the correct BibTeX `booktitle`.

**Open items:** `address` and `month` per symposium year are still not stored. These could be added to `DownloadSource` (alongside `name`/`url`/`notes`) to enable full BibTeX generation.

---

## [2026-05-31] claude-sonnet-4-6 — wire download_pdf strategy step for ATRD PDF fetching

**Action:** Added `download_pdf` step type execution. The searcher's `/download_atrd_paper` endpoint now returns raw PDF bytes (not a JSON path). Added `_call_pdf_download` (POST, expects `application/pdf` response) and `_apply_download_pdfs` (iterates candidates, saves each PDF to `pdf/<dest_subdir>/<title_slug>.pdf`, sets `pdf_path`). Wired into `_search_papers_for_venue` behind a `download_pdfs=True` flag so Search (preview) never triggers PDF downloads — only the full Download button does. Added `download_pdf` step to `strategies/atrd.json`. `atm_seminar` inherits it automatically.

**Files changed:**
- `api/routes/venues.py` — added `PDF_DIR` import; `_call_pdf_download`, `_apply_download_pdfs` helpers; `download_pdfs` flag on `_search_papers_for_venue`; `download_pdfs=True` in `download_papers_for_conference_year`
- `strategies/atrd.json` — added `download_pdf` step before `generate_doi`
- `VERSION.md` — bumped to `paper-library-v0.1.71`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** PDFs saved to `pdf/<venue_slug>/<year>/<title_slug>.pdf` using existing `PDF_DIR`. Papers that already have `pdf_path` are skipped (idempotent). Download errors are stored in `pdf_error` on the candidate dict rather than aborting the whole batch. `download_pdf` runs before `generate_doi` in the step order so the PDF is fetched with the original paper record, and DOI is assigned after.

**Open items:** `pdf_error` field on candidates is not persisted to MongoDB — errors are visible in the download response but not stored. A future improvement could log per-paper errors to the paper record.

---

