# AGENTS.md

Guidance for programming agents contributing to this repository.

## 1. Mission

Maintain a self-hosted paper metadata and PDF reference store deployed inside a Debian-based Proxmox LXC container:

- `config/` — environment-driven settings dataclass.
- `services/` — Pydantic models and Motor/MongoDB data layer.
- `api/` — FastAPI HTTP interface for paper CRUD, search, and bulk upsert.
- `scripts/` — CLI tools for importing searcher results.
- `deploy/` — Proxmox LXC provisioning and systemd service management.

Prioritize correctness, idempotent writes, and stable API contracts.

## 2. Repository Scope

```
paper-library/
├── api/
│   ├── main.py               # FastAPI app, lifespan, route registration, UI page routes
│   ├── routes/
│   │   ├── papers.py         # CRUD + search/filter + PDF upload endpoints
│   │   ├── venues.py         # Venue CRUD + LLM prefill endpoints
│   │   └── health.py         # GET /health
│   └── static/               # Server-rendered browser pages
│       ├── addvenue.html     # Add/edit venue with AI prefill
│       ├── venues.html       # All venues table
│       ├── conf.html         # Conferences filtered table
│       └── journals.html     # Journals filtered table
├── services/
│   ├── mongo.py              # Motor client, db/collection accessors
│   ├── models.py             # Pydantic models for Paper, VenueRecord, etc.
│   └── venues.py             # Azure OpenAI venue prefill helper
├── config/
│   └── settings.py           # Frozen dataclass from env vars
├── scripts/
│   └── import_searcher.py    # CLI: read searcher JSON output → bulk upsert
├── deploy/
│   ├── proxmox_deploy.sh     # Creates LXC, installs MongoDB + API service
│   ├── restart.sh            # Restarts services in dependency order
│   └── update.sh             # git pull + pip install + restart
├── venues/                   # JSON venue store (<slug>.json per venue)
│   └── .gitkeep
├── .env.example
├── requirements.txt
├── VERSION.md
├── AGENT_LOG.md
├── AGENTS.md
├── CLAUDE.md
├── ARCHITECTURE.md
└── history/                  # archived AGENT_LOG entries (YYYY-MM.md)
```

If you add or change behavior in any module, update `ARCHITECTURE.md` in the same change if the data flow or endpoint contracts change.

## 3. Runtime Services

Two services run natively inside the LXC (no Docker):

| Service         | Description                     | Port  | Binding        |
|-----------------|---------------------------------|-------|----------------|
| `mongod`        | MongoDB 7.0 (native apt)        | 27017 | localhost only |
| `paper-library` | FastAPI metadata API (uvicorn)  | 8000  | 0.0.0.0        |

**Never expose MongoDB port 27017 externally.** It must listen on localhost inside the LXC only.

## 4. Deployment Policy

- Production: single Debian-based Proxmox LXC with `systemd`.
- MongoDB installed from the official MongoDB 7.0 apt repository (no Docker).
- Python environment lives at `/opt/paper-library-env/`.
- App code lives at `/opt/paper-library/`.
- Activate with: `source /opt/paper-library-env/bin/activate`
- To start the API: `uvicorn api.main:app --host 0.0.0.0 --port 8000`
- systemd units: `mongod.service` (installed by apt) and `paper-library.service` (written by deploy script).

## 5. Agent Roles

- **Implementer agent**: owns code changes inside `api/`, `services/`, `config/`, or `scripts/`.
- **Documentation agent**: owns `ARCHITECTURE.md`, root `.env.example`.
- **Verification agent**: runs syntax checks and smoke tests.

When using multiple agents in parallel, assign disjoint file ownership.

## 6. Coding Rules

- Python 3.10+ compatible syntax.
- Async throughout — use `motor` (async MongoDB driver) with `FastAPI`.
- DOI is the canonical deduplication key. All writes use upsert-by-DOI.
- `created_at` is set only on first insert (`$setOnInsert`); `updated_at` is updated on every write.
- Preserve current API contracts unless explicitly asked to break them.
- Keep endpoints deterministic and JSON-serializable.
- Validate all user inputs at system boundaries.
- Fail with explicit HTTP status and message.
- Never log or expose secrets.
- Keep external dependencies minimal.
- For standalone scripts, prefer flat top-level execution wrapped in `main()` with `if __name__ == "__main__"`.

## 7. Python Environment Rules (Required)

- Virtual environment at `/opt/paper-library-env/` for production; any local venv is acceptable for development.
- Install deps: `pip install -r requirements.txt`
- Re-run whenever `requirements.txt` changes.
- Do not use system/global `python3` or `pip` for project tasks unless inside the activated venv.

## 8. Version Update Rule

- Whenever code changes are made, automatically increment the patch version in `VERSION.md` at the project root (e.g. `v0.1.0` → `v0.1.1`).
- If the user says `update version name to <new>`, use that exact name instead.
- Format: `VERSION_NAME=<version name>`

## 9. Safety and Security

- Never expose MongoDB port 27017 externally without authentication.
- Accept only filesystem paths provided explicitly by the caller.
- Never write secrets to logs or response bodies.
- DOI index is unique at the database level — duplicate inserts will be rejected by MongoDB.

## 10. Agent Handoff Log (Mandatory)

`AGENT_LOG.md` at the repo root is the shared memory between agents. Every agent — Claude, Codex, or any other — that touches this repo must participate in the loop.

**Before starting any task:**
1. Read `AGENT_LOG.md` in full.
2. Note any open items relevant to your task.

**After completing any task:**
1. Prepend a new entry at the top of `AGENT_LOG.md` (newest entry first).
2. Use this exact format:

```markdown
## [YYYY-MM-DD] <agent-name> — <one-line summary>
**Action:** What was done and why.
**Files changed:** List each file modified, created, or deleted.
**Decisions:** Any non-obvious choices made and the reasoning.
**Open items:** Anything left incomplete, deferred, or worth a follow-up.
```

3. If `AGENT_LOG.md` exceeds 200 lines, move all entries older than the 10 most recent into `history/YYYY-MM.md` (create the file if needed), then leave only the 10 most recent entries in `AGENT_LOG.md`.

Do not skip this step. It is how the next agent — human or AI — knows what happened.

## 11. Change Workflow

1. Read `AGENT_LOG.md` to understand recent context and open items.
2. Identify which module is affected.
3. Read that module and `config/settings.py`.
4. Implement the smallest coherent change.
5. Run syntax checks for affected files.
6. Update `ARCHITECTURE.md` if data flow or endpoint contracts changed.
7. Update `.env.example` if new config keys were added.
8. Increment patch version in `VERSION.md`.
9. Prepend a new entry to `AGENT_LOG.md` (see §10).
10. Summarize changes, assumptions, and residual risks.
11. Output a git commit message only if the user asks (see §12).

## 12. Git Commit Message (On Request Only)

Only output a git commit message when the user explicitly asks for one (e.g. "give me a commit message", "what's the commit?", "git message").

When requested, cover **all changes since the last commit** — not just the most recent task. Check `git diff` or `git status` to identify everything that has changed.

Format:

```
<type>(<scope>): <short imperative summary under 72 chars>

<body — what changed and why, wrapped at 72 chars. List each
logical change as a bullet if multiple changes are bundled.>

Files: <comma-separated list of all changed files>
Version: <current VERSION_NAME value>
```

**Type** must be one of: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`.
Use `feat` if any new capability was added, even alongside fixes or docs.
**Scope** is the broadest top-level area affected, or `root` for repo-level changes.

Output the commit message in a fenced code block so the user can copy it directly.
Do not include `.env` or any file matching `.gitignore`.

## 13. Definition of Done

- Code is syntactically valid Python.
- `doi` index is unique; duplicate inserts are rejected at the DB level.
- Bulk upsert is idempotent — sending the same payload twice produces identical DB state.
- Existing records are not wiped on re-ingest (upsert-by-DOI, not replace).
- Endpoint behavior matches `ARCHITECTURE.md`.
- New config keys are documented in `.env.example`.
- `VERSION.md` is updated on every code change.
