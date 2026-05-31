# AGENT_LOG.md

Shared handoff log between agents. Newest entry first.
Read this before starting any task. Append an entry after completing any task.
Archive to `history/YYYY-MM.md` when this file exceeds 200 lines (keep 10 most recent).

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

## [2026-05-31] claude-sonnet-4-6 — improve submission deadline prefill and rename label

**Action:** Sharpened the `due_date_month` LLM prompt rule to instruct the model to use the next upcoming submission deadline month, falling back to the most recently known one. Renamed the "Due Date" label to "Submission Deadline" in `addconf.html` and all three listing pages.

**Files changed:**
- `services/venues.py` — updated `due_date_month` prompt rule with next-upcoming/fallback instruction
- `api/static/addconf.html` — form label "Due Date" → "Submission Deadline"
- `api/static/conf.html` — table header "Due Date" → "Submission Deadline"
- `api/static/venues.html` — table header "Due Date" → "Submission Deadline"
- `api/static/journals.html` — table header "Due Date" → "Submission Deadline"
- `VERSION.md` — bumped to `paper-library-v0.1.43`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** No new fields needed — `due_date_month` already stores a month name. The prompt change is sufficient to guide the LLM toward the most actionable deadline value. Journals show the column as `—` since the rule explicitly excludes them.

**Open items:** None.

---

## [2026-05-31] claude-sonnet-4-6 — remove dead model fields and fix chip XSS in add pages

**Action:** Removed `ProceedingsYear` model class and `all_years`, `year_start`, `year_end`, `proceedings_years` fields from `VenueRecord` — all remnants of the removed proceedings URL feature. Removed `proceedings_years: []` from `getForm()` in both `addconf.html` and `addjournal.html`. Fixed an XSS risk in both pages' chip lists where `v.short_name` and `v.slug` were interpolated directly into `innerHTML`; replaced with DOM API (`textContent`, element construction).

**Files changed:**
- `services/models.py` — removed `ProceedingsYear` class; removed `all_years`, `year_start`, `year_end`, `proceedings_years` from `VenueRecord`
- `api/static/addconf.html` — removed `proceedings_years` from `getForm()`; fixed chip `innerHTML` → DOM construction
- `api/static/addjournal.html` — same as above
- `VERSION.md` — bumped to `paper-library-v0.1.42`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** `proceedings_years` was already sent as `[]` by both forms and served no purpose in stored JSON. The XSS risk is low in a self-hosted tool, but the fix is trivial and correct.

**Open items:** Existing venue JSON files may still contain `all_years`, `year_start`, `year_end`, `proceedings_years` keys — harmless on read since Pydantic ignores extra fields by default.

---

## [2026-05-31] claude-sonnet-4-6 — remove addvenue legacy artifact

**Action:** Confirmed `api/static/addvenue.html` was already deleted by Codex and no `/addvenue` route exists in `api/main.py`. No code changes needed — this entry documents the intentional removal.

**Files changed:**
- `VERSION.md` — bumped to `paper-library-v0.1.41`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** User confirmed `/addvenue` is no longer needed. All nav links already point to `/addconf` and `/addjournal`.

**Open items:** None.

---

## [2026-05-31] codex-gpt-5 — split venue creation into dedicated addconf/addjournal pages

**Action:** Replaced the single mixed add page flow with dedicated conference and journal creation pages. Added `/addconf` and `/addjournal` routes, kept `/addvenue` as a compatibility redirect to `/addconf`, and updated navigation links across list pages to point to the new forms.

**Files changed:**
- `api/main.py` — added `/addconf` and `/addjournal`; redirected `/addvenue` to `/addconf`
- `api/static/addconf.html` — new conference-specific add page (fixed `type: "conference"`, month due-date input)
- `api/static/addjournal.html` — new journal-specific add page (fixed `type: "journal"`)
- `api/static/venues.html` — nav links updated to new add pages
- `api/static/conf.html` — nav links updated to new add pages
- `api/static/journals.html` — nav links updated to new add pages
- `ARCHITECTURE.md` — documented new UI routes and backward-compatible `/addvenue` redirect
- `AGENTS.md` — repository scope tree updated with new static pages
- `VERSION.md` — bumped to `paper-library-v0.1.40`

**Decisions:** Kept `addvenue.html` in the repo for compatibility while routing traffic to `/addconf` to avoid breaking existing bookmarks. Conference and journal forms now enforce their type client-side by sending a fixed `type` value in payloads.

**Open items:** `api/static/addvenue.html` remains as a legacy artifact and can be removed in a future cleanup pass if no external links depend on it.

---

## [2026-05-31] codex-gpt-5 — add conference due-date month field and display columns

**Action:** Added a `due_date_month` field to venue creation and persistence, validated month names at the model boundary, and surfaced the value on the static venue listing pages. Updated the venue prefill contract prompt and architecture documentation accordingly.

**Files changed:**
- `services/models.py` — added `due_date_month` to `VenueRecord` with month-name validator
- `api/routes/venues.py` — included `publisher` and `due_date_month` in `GET /api/venues` list payload
- `services/venues.py` — updated prefill prompt schema to include `due_date_month`
- `api/static/addvenue.html` — added conference-only Due Date month dropdown and form wiring
- `api/static/venues.html` — added Due Date column to all-venues table
- `api/static/conf.html` — added Due Date column to conferences table
- `api/static/journals.html` — added Due Date column to journals table
- `ARCHITECTURE.md` — documented `/api/venues` endpoint map and `due_date_month` contract
- `VERSION.md` — bumped to `paper-library-v0.1.39`

**Decisions:** `due_date_month` is optional and normalized to Title Case month names (`January`..`December`) or empty string. The Due Date input is shown only when `type=conference` in the add form and cleared for non-conference types to avoid stale values.

**Open items:** Existing venue JSON files do not have `due_date_month`; they will display as `—` until edited/resaved.

---

## [2026-05-31] claude-sonnet-4-6 — serve venues/conferences/journals as webpages at clean URLs

**Action:** Moved the venues JSON API from `/venues` to `/api/venues` so the browser-friendly paths could be claimed. `/venues` now serves `venues.html`, `/conferences` serves `conf.html`, `/journals` serves `journals.html`. Updated all `fetch()` calls, `href` attributes, and nav links across all four static HTML files.

**Files changed:**
- `api/main.py` — router prefix changed to `/api/venues`; page routes updated to `/venues`, `/conferences`, `/journals`
- `api/static/venues.html` — nav links and fetch/delete calls updated to `/api/venues`
- `api/static/conf.html` — nav links and fetch/delete calls updated
- `api/static/journals.html` — nav links and fetch/delete calls updated
- `api/static/addvenue.html` — fetch calls (prefill, save, list) updated to `/api/venues`
- `VERSION.md` — bumped to `paper-library-v0.1.38`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** All venue CRUD/data endpoints live under `/api/venues/*`. The three page URLs (`/venues`, `/conferences`, `/journals`) are human-facing and return HTML. `/conf` is gone — the canonical path is `/conferences`.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-31] claude-sonnet-4-6 — remove URL auto-lookup; user enters main page URL manually

**Action:** Removed per-year proceedings URL discovery (OpenAlex and IEEE Xplore lookups) from the add-venue flow. The Access URL field is now a plain text input labeled "Main page URL" that the user fills in. Removed the proc-list checkbox UI, `buildProcList`, `loadProceedingsUrls`, `toggleAllProc`, `applyYearsSince`, and the years-since filter from `addvenue.html`. Removed the `GET /venues/proceedings` endpoint and its `ieee_proceedings_urls` import from `api/routes/venues.py`. Removed `openalex_proceedings_urls`, `ieee_proceedings_urls`, and `_ieee_fetch_articles` from `services/venues.py`. Removed `openalex_api_key` from `Settings` and `.env.example`.

**Files changed:**
- `api/static/addvenue.html` — stripped proc-list UI and all URL-lookup JS
- `api/routes/venues.py` — removed `/proceedings` endpoint and `ieee_proceedings_urls` import
- `services/venues.py` — removed `openalex_proceedings_urls`, `ieee_proceedings_urls`, `_ieee_fetch_articles`; removed proceedings enrichment from `prefill_venue`
- `config/settings.py` — removed `openalex_api_key` field
- `.env.example` — removed `OPENALEX_API_KEY`
- `VERSION.md` — bumped to `paper-library-v0.1.37`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** The proceedings URL search produced semantically wrong data (OpenAlex `/sources` returns one series-level record, not per-year links) and had a broken gate in `prefill_venue`. Simpler to let the user paste the URL they already know.

**Open items:** `ieee_xplore_api_key` remains in Settings for future paper metadata ingestion. `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-28] claude-sonnet-4-6 — add OpenAlex as default proceedings source

**Action:** Added `openalex_proceedings_urls()` using the OpenAlex `/sources` API. Works for any publisher (not just IEEE). Updated `ieee_proceedings_urls()` to try OpenAlex first and fall back to IEEE Xplore. Added `OPENALEX_API_KEY` to Settings, `.env.example`, and `.env.dev`. IEEE Xplore is preserved for future paper metadata ingestion.

**Files changed:**
- `services/venues.py` — `openalex_proceedings_urls()`; `ieee_proceedings_urls()` tries OpenAlex first
- `config/settings.py` — added `openalex_api_key` field
- `.env.example` — documented `OPENALEX_API_KEY`; updated IEEE note
- `.env.dev` — added `OPENALEX_API_KEY`
- `VERSION.md` — bumped to `paper-library-v0.1.36`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** OpenAlex URLs point to `homepage_url` when available, otherwise the OpenAlex source page (`https://openalex.org/<id>`). OpenAlex returns ~10 results for DASC (coverage gaps for older years); IEEE Xplore returns 30. For non-IEEE venues OpenAlex is the only option.

**Open items:** IEEE Xplore will be used later for paper metadata ingestion. `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — fix proc-list not rendering: use display:block not display:''

**Action:** `buildProcList` was setting `list.style.display=''` to show the list, which reverts to the CSS class default of `display:none`. Changed to `display:'block'` so the list is explicitly shown after items are appended.

**Files changed:**
- `api/static/addvenue.html` — `list.style.display='block'` in `buildProcList`
- `VERSION.md` — bumped to `paper-library-v0.1.33`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** Setting `display:''` removes the inline style and lets the stylesheet rule win — which is `display:none`. Must use an explicit value.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

---

## [2026-05-27] claude-sonnet-4-6 — fix proceedings lookup using typo'd prefill input

**Action:** The proceedings fallback in `populate()` was using the raw prefill bar text as the IEEE Xplore query name. If the user typed a misspelling (e.g. "avioincs"), the API returned zero results. Fixed by preferring `d.long_name` (LLM-corrected) over the raw input. Order is now: long_name → short_name → prefill input.

**Files changed:**
- `api/static/addvenue.html` — `populate()` fallback name order corrected
- `VERSION.md` — bumped to `paper-library-v0.1.32`
- `AGENT_LOG.md` — prepended this entry

**Decisions:** The LLM always normalises the venue name correctly, so `d.long_name` is the most reliable source for the IEEE query.

**Open items:** `ARCHITECTURE.md` still needs a venue endpoints section.

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

