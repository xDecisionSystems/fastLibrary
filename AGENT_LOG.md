# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

---

## [2026-06-01] codex-gpt-5 — harden download retry config parsing and recover UI after polling failures

**Action:** Reviewed the most recent Claude changes (`v0.1.99`–`v0.2.1`) with focus on Download All polling and transient PDF retry behavior. Applied two follow-up fixes: (1) hardened `download_pdf` retry settings by coercing invalid/negative `retries` and `backoff` values to safe defaults, and fixed retry attempt labels to reflect actual attempt counts; (2) improved venue-page polling failure handling so a polling error no longer leaves rows stuck in running state, and Download All now reports how many starts actually succeeded.

**Files changed:**
- `api/routes/venues.py` — sanitized retry/backoff config handling and corrected retry attempt accounting in `_call_pdf_download`
- `api/static/venue.html` — polling error recovery updates row/actions and reloads when appropriate; `downloadYear` now returns success/failure; `downloadAll` reports partial start failures accurately
- `VERSION.md` — bumped to `paper-library-v0.2.2`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Kept linear backoff behavior unchanged while making malformed strategy values non-fatal. UI failure handling now favors quick recovery to server-authoritative state instead of leaving stale in-progress controls.

**Open items:** None.

---

## [2026-06-01] codex-gpt-5 — remove Per-Year Proceedings notes/location/month columns from conference UIs

**Action:** Updated conference-facing Per-Year Proceedings tables to remove visible `notes`, `location`, and `month` columns as requested. Applied this in both conference creation and conference edit pages. To avoid unintended data loss for existing records, hidden per-row metadata is preserved via row `dataset` attributes and still sent back in `download_sources` on save.

**Files changed:**
- `api/static/addconf.html` — Per-Year Proceedings table now shows only `Year`, `URL`, and delete action; hidden `notes` preserved via row dataset
- `api/static/venue.html` — Per-Year Proceedings table now shows only `Year`, `URL`, and delete action; hidden `location`, `month`, and `notes` preserved via row dataset
- `VERSION.md` — bumped to `paper-library-v0.1.98`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Kept non-visible source metadata in payloads to preserve backward compatibility with existing conference records and BibTeX-related fields while simplifying the UI.

**Open items:** None.

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

## [2026-06-01] claude-sonnet-4-6 — retry logic for transient PDF download failures

**Action:** `IncompleteRead` and 502/503/504 errors from the searcher are transient (dropped connections, Google Drive throttling). Added retry-with-back-off to `_call_pdf_download`: up to `retries` attempts with `backoff * attempt` seconds between each. `IncompleteRead` and gateway errors (502/503/504) are retried; non-retryable HTTP errors (e.g. 404, 400) raise immediately. Added `retries` and `backoff` params to both sequential and parallel download paths, read from the strategy step config. Set `retries: 3, backoff: 5` in `strategies/atrd.json`.

**Files changed:**
- `api/routes/venues.py` — `_call_pdf_download` accepts `retries`/`backoff`; both download functions pass them from step config
- `strategies/atrd.json` — `retries: 3`, `backoff: 5` added to `download_pdf` step config
- `VERSION.md` — bumped to `paper-library-v0.2.1`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Back-off is linear (`5s * attempt`) — attempt 1 waits 5s, attempt 2 waits 10s. Keeps it simple and predictable. `IncompleteRead` is imported from `http.client` at call time (no new top-level import needed). 502 is retried because it came directly from the error report; 503/504 are retried for the same reason (transient gateway issues).

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — fix parallel download rows disappearing during Download All

**Action:** When multiple years were downloading simultaneously via Download All, each year's poll loop called `loadPapers()` on completion, which re-rendered the entire table and wiped the live progress indicators for still-running years. Fixed by checking `Object.keys(_pollTimers).length === 0` before calling `loadPapers()` — the full reload only happens when the last active poll finishes. In-progress rows remain visible and update in-place until all downloads complete.

**Files changed:**
- `api/static/venue.html` — `_startPolling` completion handler guards `loadPapers()` with active-poll check
- `VERSION.md` — bumped to `paper-library-v0.2.0`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `_applyTaskToRow` already updates the completed row's status and actions in-place, so skipping `loadPapers()` while other polls are active loses no information — the row just doesn't get the server-authoritative count until the final reload.

**Open items:** None.

---

## [2026-06-01] claude-sonnet-4-6 — remove max-width caps from all non-modal pages

**Action:** Removed `max-width` constraints from page-level cards and nav bars across all narrow pages so content fills the full viewport width. Modals and detail panels retain their `max-width` for readability. Pages updated: `venue.html` (`.card`, `.papers-card`, `nav`), `addconf.html` (`.card`, `nav`), `addjournal.html` (`.card`, `nav`), `tags.html` (`.card`), `admin.html` (`.card`), `strategies.html` (`.new-card`).

**Files changed:**
- `api/static/venue.html`, `addconf.html`, `addjournal.html`, `tags.html`, `admin.html`, `strategies.html`
- `VERSION.md` — bumped to `paper-library-v0.1.99`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Listing pages (venues.html, conf.html, journals.html, papers.html) already had no max-width on their cards from an earlier change — only the form/detail pages needed updating.

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

