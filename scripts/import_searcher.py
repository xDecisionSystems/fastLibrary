#!/usr/bin/env python3
"""
Read a searcher JSON output file (envelope with a 'results' array) and
bulk-upsert all records into the paper library via POST /papers/bulk.

Usage:
    python scripts/import_searcher.py results.json [--api-url http://localhost:8000]
"""

import argparse
import json
import sys

import urllib.request
import urllib.error


def main() -> None:
    parser = argparse.ArgumentParser(description="Import searcher results into paper library.")
    parser.add_argument("file", help="Path to searcher JSON output file.")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Base URL of the paper library API (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--overwrite-missing-fields",
        action="store_true",
        help="If set, omitted fields overwrite existing values with model defaults.",
    )
    parser.add_argument(
        "--overwrite-duplicate-doi",
        action="store_true",
        help="If set, duplicate DOI entries in this file keep the last record.",
    )
    args = parser.parse_args()

    with open(args.file, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    if isinstance(data, dict):
        records = data.get("results", [])
    elif isinstance(data, list):
        records = data
    else:
        print(f"ERROR: Unexpected JSON structure in {args.file}", file=sys.stderr)
        sys.exit(1)

    valid = []
    skipped = 0

    for record in records:
        doi = record.get("doi", "").strip()
        if not doi:
            title = record.get("title", "(no title)")
            print(f"WARNING: Skipping record with no DOI — title: {title!r}")
            skipped += 1
            continue
        valid.append(record)

    if not valid:
        print(f"Processed {len(records)} records: 0 upserted, 0 modified, {skipped} skipped (no DOI).")
        return

    payload = json.dumps(
        {
            "papers": valid,
            "overwrite_missing_fields": args.overwrite_missing_fields,
            "overwrite_duplicate_doi": args.overwrite_duplicate_doi,
        }
    ).encode("utf-8")
    url = args.api_url.rstrip("/") + "/api/papers/bulk"

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"ERROR: HTTP {exc.code} from {url}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"ERROR: Could not reach {url}: {exc.reason}", file=sys.stderr)
        sys.exit(1)

    upserted = result.get("upserted", 0)
    modified = result.get("modified", 0)
    errors = result.get("errors", [])

    print(
        f"Processed {len(records)} records: "
        f"{upserted} upserted, {modified} modified, {skipped} skipped (no DOI)."
    )
    if errors:
        print(f"  {len(errors)} error(s):")
        for err in errors:
            print(f"    doi={err.get('doi')} — {err.get('error')}")


if __name__ == "__main__":
    main()
