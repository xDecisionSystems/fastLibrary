from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

_VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION.md"


def _read_version() -> str:
    try:
        for line in _VERSION_FILE.read_text().splitlines():
            if line.startswith("VERSION_NAME="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return "unknown"


VERSION = _read_version()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": VERSION}
