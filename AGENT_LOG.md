# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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

## [2026-05-31] claude-sonnet-4-6 — synthetic DOI generation for ATRD/ATM Seminar papers

**Action:** ATRD Symposium and ATM Seminar papers are not registered with DOI.org. Added a `generate_doi` strategy step type that generates a deterministic synthetic DOI (`10.0000/<namespace>.<year>.<title_slug>`) for any paper missing one, and sets `doi_synthetic: true`. Added `doi_synthetic: bool` field to `Paper` and `PaperUpdate` models. Wired `generate_doi` step execution into `_search_papers_for_venue` so it runs after the fetch step for any strategy that includes it. Updated `_to_paper_model` to pass through `doi_synthetic` and also map ATRD-specific response fields (`full_paper_url` → `pdf_link`, `section` → tag). Added `generate_doi` step to `strategies/atrd.json` and created `strategies/atm_seminar.json` (extends `atrd`, no step overrides needed).

**Files changed:**
- `services/models.py` — added `doi_synthetic: bool = False` to `Paper`; `doi_synthetic: Optional[bool]` to `PaperUpdate`
- `api/routes/venues.py` — added `_make_title_slug`, `_apply_generate_doi` helpers; wired `generate_doi` step in `_search_papers_for_venue`; updated `_to_paper_model` for `doi_synthetic`, `full_paper_url`, `section`
- `strategies/atrd.json` — added `generate_doi` step after `fetch_papers`
- `strategies/atm_seminar.json` — new strategy extending `atrd` with no overrides
- `VERSION.md` — bumped to `paper-library-v0.1.70`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Synthetic DOI format `10.0000/<slug>.<year>.<title_slug>` is deterministic so re-running a download is idempotent — same paper always gets same DOI. `section` from ATRD response is appended as a tag so topic classification is preserved. `atm_seminar` extends `atrd` rather than duplicating steps — any future change to ATRD fetch/DOI logic propagates automatically.

**Open items:** After deploying, re-save the ATM Seminar venue in the UI to auto-select `strategy: "atm_seminar"`, then trigger downloads.

---

## [2026-05-31] claude-sonnet-4-6 — recompute slug from short_name on venue update and redirect

**Action:** `update_venue` now recomputes the slug from the incoming `short_name` on every save. If the new slug differs from the URL slug, the old file is deleted and the new file is written with the new slug, then the response includes `slug: <new_slug>`. The venue edit page (`venue.html`) detects a slug change in the response and redirects to `/venues/<new_slug>` using `window.location.replace` so the back button does not return to the stale URL. A 409 is returned if the new slug would collide with an existing venue. Also fixed a stale `'_default'` fallback in `getForm()` in `venue.html`.

**Files changed:**
- `api/routes/venues.py` — `update_venue` recomputes slug, renames file, raises 409 on collision
- `api/static/venue.html` — `doSave()` redirects on slug change; `getForm()` strategy fallback `'_default'` → `''`
- `VERSION.md` — bumped to `paper-library-v0.1.69`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Used `window.location.replace` (not `assign`) so the stale `/venues/<old-slug>` URL is removed from browser history — pressing back goes to the venues list rather than a 404. `_default_strategy_for_slug` is called with the new slug so auto-selection also reflects the rename.

**Open items:** The existing ATRD Symposium venue on the deployed server (`us_europe_atm_r_d_seminar`) needs to be re-saved after the update is deployed — saving will rename it to `atrd_symposium` and auto-select `strategy: "atrd"`.

---

## [2026-05-31] claude-sonnet-4-6 — remove _default strategy fallback; blank means no strategy

**Action:** Removed all hardcoded `"_default"` fallbacks throughout the codebase. `VenueRecord.strategy` now defaults to `""`. `_default_strategy_for_slug` returns `""` when no matching file exists. `_build_searcher_request` treats a blank strategy as "no strategy" — skips resolution and falls through to plain POST on `settings.searcher_api_base_url`. `list_venues` returns `""` for venues without a strategy field. Auto-select condition in `create_venue`/`update_venue` now triggers on blank rather than `"_default"`.

**Files changed:**
- `services/models.py` — `strategy` field default `"_default"` → `""`
- `api/routes/venues.py` — `_default_strategy_for_slug` returns `""`; `_build_searcher_request` blank-strategy path; `list_venues` fallback `""`; create/update condition uses blank check
- `VERSION.md` — bumped to `paper-library-v0.1.68`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Blank strategy is now the canonical "no strategy configured" state. Venues that still have `"_default"` in their stored JSON will read that string back on `GET` — they will attempt to resolve a `_default` strategy file, which does exist, so they continue to work. To fully clean those up, re-save via the venue edit page.

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — auto-select strategy by venue slug on create/update

**Action:** Added `_default_strategy_for_slug(slug)` helper that returns the slug if a matching `strategies/<slug>.json` exists, otherwise `"_default"`. Applied in both `create_venue` and `update_venue`: when the strategy field is `"_default"` (i.e. not explicitly overridden by the caller), it is replaced with the slug-matched strategy. This means creating or saving an ATRD venue automatically sets `strategy: "atrd"` without any manual UI step.

**Files changed:**
- `api/routes/venues.py` — added `_default_strategy_for_slug`; applied in `create_venue` and `update_venue`
- `VERSION.md` — bumped to `paper-library-v0.1.67`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Only applies when strategy is still `"_default"` — an explicit user selection is never overwritten. Works at both create and update time, so re-saving an existing venue with `_default` also upgrades it to the slug-matched strategy.

**Open items:** Existing ATRD venue on the deployed server will not be auto-updated until it is re-saved via the venue edit page (which will trigger `update_venue` and apply the auto-select).

---
