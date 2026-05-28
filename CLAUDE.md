# CLAUDE.md

Repository instructions for Claude-based programming agents.

## Repository Structure

A self-hosted paper metadata and PDF reference store deployed in a single Proxmox LXC. No Docker. All components run natively:

- `config/` — environment-driven frozen settings dataclass
- `services/` — Pydantic models (`models.py`) and Motor/MongoDB data layer (`mongo.py`)
- `api/` — FastAPI service (port 8000) with paper CRUD and bulk-upsert endpoints
- `scripts/` — CLI import tool for searcher JSON output
- `deploy/` — Proxmox LXC provisioning and service management scripts

## Deployment Policy

- Production: Debian-based Proxmox LXC with `systemd`.
- Python environment: `/opt/paper-library-env/` (created by `deploy/proxmox_deploy.sh`).
- App code: `/opt/paper-library/`.
- MongoDB 7.0 installed natively from the official apt repository; never via Docker.
- MongoDB listens on localhost only — never expose port 27017 externally.
- Shared env lives at `.env` in the project root; `.env.example` documents all keys.
- Do not add additional deployment targets unless explicitly requested.

## 1. Environment Requirement (Mandatory)

- Production venv: `/opt/paper-library-env/`
- Local development: any venv at the project root is acceptable.
- Install deps: `pip install -r requirements.txt`
- Re-run whenever `requirements.txt` changes.
- Do not use system/global `python3` or `pip` for project tasks.
- Prefer explicit venv activation: `source /opt/paper-library-env/bin/activate`

## 2. Standard Command Patterns

- Install deps: `pip install -r requirements.txt`
- Run API locally: `uvicorn api.main:app --host 127.0.0.1 --port 8000`
- Import searcher results: `python scripts/import_searcher.py results.json`
- Syntax check all modules:
  ```
  python3 -m py_compile api/main.py api/routes/papers.py api/routes/health.py \
    api/routes/venues.py services/mongo.py services/models.py services/venues.py \
    config/settings.py scripts/import_searcher.py
  ```

## 3. Version Update Rule

- Whenever code changes are made, automatically increment the patch version in `VERSION.md` at the project root (e.g. `v0.1.0` → `v0.1.1`).
- If the user says `update version name to <new version name>`, use that exact name instead.
- Format: `VERSION_NAME=<version name>`
- Keep the key name exactly `VERSION_NAME`.

## 4. Change Hygiene

- Update `ARCHITECTURE.md` whenever data model or endpoint contracts change.
- Update `.env.example` whenever new config keys are introduced; also update `.env.dev` with the same keys (use safe local defaults, leave secrets blank).
- Keep API responses stable unless a breaking change is explicitly requested.
- Validate all input at system boundaries and return clear HTTP errors.

## 5. Security Basics

- Never expose secrets in logs or responses.
- MongoDB must only listen on localhost (port 27017) — do not expose externally without authentication.
- DOI uniqueness is enforced at the database level via a unique index.

## 6. Git Commit Message (On Request Only)

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

## 7. Agent Handoff Log (Mandatory)

`AGENT_LOG.md` at the repo root is the shared memory between agents. Every agent that touches this repo must participate in the loop.

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
