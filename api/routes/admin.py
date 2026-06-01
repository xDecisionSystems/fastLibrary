import json

from fastapi import APIRouter

from config.settings import PDF_DIR, TASKS_DIR, VENUES_DIR
from services import mongo

router = APIRouter(tags=["admin"])


@router.post("/delete-all-papers")
async def delete_all_papers():
    deleted_papers = await mongo.delete_all_papers()
    cleared_cache = await mongo.clear_search_cache()

    # Delete all PDF files
    deleted_pdfs = 0
    pdf_errors: list[str] = []
    if PDF_DIR.exists():
        for f in PDF_DIR.rglob("*.pdf"):
            try:
                f.unlink()
                deleted_pdfs += 1
            except Exception as exc:
                pdf_errors.append(str(exc))

    # Delete persisted async task-state files.
    deleted_task_states = 0
    task_errors: list[str] = []
    if TASKS_DIR.exists():
        for f in TASKS_DIR.glob("*.json"):
            try:
                f.unlink()
                deleted_task_states += 1
            except Exception as exc:
                task_errors.append(str(exc))

    # Reset paper_downloads in all venue JSON files
    reset_venues = 0
    venue_errors: list[str] = []
    VENUES_DIR.mkdir(parents=True, exist_ok=True)
    for venue_file in sorted(VENUES_DIR.glob("*.json")):
        if venue_file.name == "_tags.json":
            continue
        try:
            doc = json.loads(venue_file.read_text(encoding="utf-8"))
            if not isinstance(doc, dict):
                continue
            if "paper_downloads" in doc:
                doc["paper_downloads"] = {}
                venue_file.write_text(json.dumps(doc, indent=2), encoding="utf-8")
                reset_venues += 1
        except Exception as exc:
            venue_errors.append(f"{venue_file.name}: {exc}")

    return {
        "deleted_papers": deleted_papers,
        "cleared_cache_entries": cleared_cache,
        "deleted_pdfs": deleted_pdfs,
        "deleted_task_states": deleted_task_states,
        "reset_venues": reset_venues,
        "errors": pdf_errors + task_errors + venue_errors,
    }
