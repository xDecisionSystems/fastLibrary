# ARCHITECTURE.md

## 1. High-Level Design

Paper Library is a single FastAPI microservice backed by native MongoDB. It sits between the searcher service (which finds and downloads papers) and the RAG system (which ingests and queries them).

```
Searcher Service  ──POST /papers/bulk──►  FastAPI (paper-library)  ──►  MongoDB
                                                   │
RAG System        ──GET  /papers?ingested=false──►  │
                  ──PATCH /papers/{doi}──────────►  │
```

**DOI is the universal paper key.** Every write is an upsert-by-DOI, so re-sending the same paper is always safe and idempotent.

## 2. Runtime Components

| Component         | Technology              | Port  | Binding        |
|-------------------|-------------------------|-------|----------------|
| `mongod`          | MongoDB 7.0 (native)    | 27017 | localhost only |
| `paper-library`   | FastAPI + uvicorn        | 8000  | 0.0.0.0        |
| Motor client      | async MongoDB driver     | —     | opened at lifespan startup |

**Motor client lifecycle:** opened in the FastAPI `lifespan` context manager at startup, closed on shutdown. Index creation (unique on `doi`; text on `title`/`tags`; compound on `source`/`publication_year`) runs once at startup.

**Pydantic validation layer:** all inbound JSON is validated against `Paper` or `PaperUpdate` before any database call.

## 3. Request Flow

### PDF upload path (POST /papers/{doi}/pdf)

1. Caller first uploads metadata via `POST /papers` (record must exist — 404 otherwise).
2. Caller then POSTs a multipart `file` to `POST /papers/{doi:path}/pdf`.
3. Route reads the full file into memory, validates magic bytes (`%PDF`), and enforces a 200 MB limit.
4. File is written to `{PDF_DIR}/{sanitized_doi}.pdf` (DOI non-alphanumeric chars replaced with `_`).
5. `pdf_path` and `updated_at` are updated on the existing record via `$set`.
6. Re-uploading silently overwrites the previous file and path — no confirmation required.
7. Response: `{"doi": ..., "pdf_path": ..., "size_bytes": N}`.

### Upsert path (POST /papers or POST /papers/bulk)

1. FastAPI deserializes and validates request body via `Paper` / `BulkUpsertRequest`; DOI is normalized and must be non-empty.
2. Route calls `mongo.upsert_paper()` or `mongo.bulk_upsert()`, passing overwrite flags.
3. MongoDB `update_one` / `bulk_write` with `upsert=True`, matching on `doi`.
4. Default behavior (`overwrite_missing_fields=false`) is sparse update: only caller-provided fields are updated + `updated_at`.
5. Overwrite behavior (`overwrite_missing_fields=true`) updates full model fields + `updated_at`; missing fields are replaced with defaults.
6. `$setOnInsert` sets `created_at` only on first insert.
7. Bulk duplicate DOI behavior:
   - `overwrite_duplicate_doi=false` rejects duplicate DOI rows in one payload (HTTP 400).
   - `overwrite_duplicate_doi=true` keeps only the last row per DOI in that payload.
8. Response returns `{"doi": ..., "action": "upserted"}` or bulk summary.

### Query/filter path (GET /papers)

1. Route builds a MongoDB filter dict from query parameters.
2. `title` param uses `$text` search (requires text index on `title`/`tags`).
3. `year_low`/`year_high` build a `publication_year` range filter.
4. `tags` param uses `$all` to match all supplied tags.
5. `mongo.count_papers()` runs for total count; `mongo.list_papers()` runs with skip/limit.
6. Datetime fields serialized to ISO 8601 strings in response.

## 4. Endpoint Map

| Method | Path                     | Body / Params              | Response                                      |
|--------|--------------------------|----------------------------|-----------------------------------------------|
| GET    | /health                  | —                          | `{"status": "ok", "version": "..."}`          |
| POST   | /papers                  | `UpsertRequest` (`paper`, `overwrite_missing_fields`) | `{"doi": "...", "action": "upserted"}` |
| POST   | /papers/bulk             | `BulkUpsertRequest` (`papers`, `overwrite_missing_fields`, `overwrite_duplicate_doi`) | `{"upserted": N, "modified": N, "errors": []}` |
| GET    | /papers                  | query params (see below)   | `{"total": N, "skip": N, "limit": N, "results": [...]}` |
| POST   | /papers/{doi:path}/pdf   | multipart `file`           | `{"doi": "...", "pdf_path": "...", "size_bytes": N}` or 404 |
| GET    | /papers/{doi:path}       | —                          | Full paper document or 404                    |
| PATCH  | /papers/{doi:path}       | `PaperUpdate`              | Updated paper document or 404                 |
| DELETE | /papers/{doi:path}       | —                          | `{"deleted": true}` or 404                    |

**GET /papers query parameters:**

| Param      | Type    | Default | Description                                 |
|------------|---------|---------|---------------------------------------------|
| title      | string  | —       | Text search on title (uses `$text` index)   |
| source     | string  | —       | Exact match on provider name                |
| year_low   | int     | —       | Minimum publication year (inclusive)        |
| year_high  | int     | —       | Maximum publication year (inclusive)        |
| ingested   | bool    | —       | Filter by RAG ingestion status              |
| tags       | string  | —       | Comma-separated; all tags must be present   |
| skip       | int     | 0       | Pagination offset                           |
| limit      | int     | 50      | Page size (max 200)                         |

**Note on DOI path encoding:** DOIs containing `/` must be URL-encoded as `%2F` by callers. The `{doi:path}` route captures the full decoded DOI including slashes.

**Upsert overwrite semantics (`overwrite_missing_fields`):**

| Value   | Behavior |
|---------|----------|
| `false` (default) | Sparse update — only fields explicitly provided in the payload are written to MongoDB. Fields absent from the payload are left untouched in the existing document. Implemented via Pydantic `model_dump(exclude_unset=True)`. |
| `true`  | Full overwrite — all model fields are written, including those that were not in the payload (they take their Pydantic default values). Existing stored values for omitted fields are overwritten with defaults. |

**Important:** "sparse" is determined by what Pydantic marks as *set* — a field is set if it appeared in the JSON input, even if its value equals the default. A field absent from the JSON input is unset and will be excluded from the `$set` operation in sparse mode.

## 5. Data Contract

MongoDB document stored in the `papers` collection:

| Field              | Type            | Set by              | Notes                              |
|--------------------|-----------------|---------------------|------------------------------------|
| `doi`              | string          | `$set`              | Required; unique index key         |
| `title`            | string          | `$set`              | Default on overwrite: `""`         |
| `authors`          | array[string]   | `$set`              | Default on overwrite: `[]`         |
| `publication_year` | int \| null     | `$set`              |                                    |
| `source`           | string          | `$set`              | Provider name (openalex, ieee, ...) |
| `url`              | string          | `$set`              | Landing page URL                   |
| `pdf_link`         | string          | `$set`              | Direct PDF URL if known            |
| `pdf_path`         | string          | `$set`              | Local filesystem path if downloaded|
| `snippet`          | string          | `$set`              | Abstract or excerpt                |
| `is_abstract`      | bool            | `$set`              | Whether snippet is a full abstract |
| `tags`             | array[string]   | `$set`              | User-assigned tags                 |
| `ingested`         | bool            | `$set`              | Whether RAG has ingested this paper|
| `updated_at`       | datetime (UTC)  | `$set`              | Updated on every upsert            |
| `created_at`       | datetime (UTC)  | `$setOnInsert`      | Set only on first insert           |

By default, only fields present in the request are written (`overwrite_missing_fields=false`). Overwrite mode writes all model fields.

## 6. Index Design

| Index                             | Type     | Purpose                                           |
|-----------------------------------|----------|---------------------------------------------------|
| `doi`                             | unique   | Deduplication key; rejects duplicate inserts      |
| `title` + `tags`                  | text     | Full-text search via `$text` operator             |
| `(source, publication_year)`      | compound | Efficient filtered list queries by provider/year  |

## 7. Configuration Model

All configuration is loaded from `.env` at import time via `python-dotenv`.

| Variable    | Required | Default                    | Description                         |
|-------------|----------|----------------------------|-------------------------------------|
| `MONGO_URI` | Yes      | —                          | MongoDB connection string           |
| `MONGO_DB`  | Yes      | —                          | Database name                       |
| `API_HOST`  | No       | `0.0.0.0`                  | uvicorn bind address                |
| `API_PORT`  | No       | `8000`                     | uvicorn bind port                   |
| `PDF_DIR`   | No       | `/opt/paper-library/pdfs`  | Local PDF storage root              |

Missing `MONGO_URI` or `MONGO_DB` raises `RuntimeError` at startup (fail fast).

## 8. Deployment Topology

```
Proxmox Host
└── LXC: paper-library[-<postfix>]
    ├── /opt/paper-library/          ← repo clone (INSTALL_DIR)
    ├── /opt/paper-library-env/      ← Python venv (VENV_DIR)
    ├── /opt/paper-library/pdfs/     ← PDF storage (PDF_DIR)
    ├── /opt/paper-library/.env      ← runtime config
    ├── systemd: mongod.service      ← MongoDB (localhost:27017)
    └── systemd: paper-library.service ← FastAPI (0.0.0.0:8000)
```

`paper-library.service` declares `After=mongod.service` and `Requires=mongod.service` so systemd always starts MongoDB first.

## 9. Integration Points

### Searcher → Paper Library

Papers are fed into the library in two ways:

1. **CLI import**: `python scripts/import_searcher.py results.json` reads a searcher JSON envelope (`{"results": [...]}`) and POSTs to `POST /papers/bulk`. Records without a DOI are skipped with a warning. Optional flags:
   - `--overwrite-missing-fields`
   - `--overwrite-duplicate-doi`
2. **Direct API call**: Searcher service POSTs to `POST /papers` (single) or `POST /papers/bulk` (batch).

Searcher field names map directly to `Paper` fields — no transformation needed.

### Paper Library → RAG System

The RAG system queries for un-ingested papers and marks them done:

1. `GET /papers?ingested=false&limit=200` — fetch batch of papers not yet in the vector store.
2. For each paper, retrieve content via `pdf_path` (local file) or `pdf_link` (remote URL).
3. After successful ingestion: `PATCH /papers/{doi}` with `{"ingested": true}`.

## 10. Planned Enhancements

- **PDF download trigger**: when a paper with `pdf_link` but no `pdf_path` is upserted, optionally queue a background download job to fetch and store it automatically (complementing the manual upload endpoint).
- **Webhook / event on insert**: emit an event (HTTP callback or message queue) when a new paper is inserted, so downstream services (e.g. RAG auto-ingest) can react immediately.
- **Full-text search on abstracts**: add `snippet` to the text index once abstract content is reliably populated.
