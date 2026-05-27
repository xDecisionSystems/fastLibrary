from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.routes import health as health_router
from api.routes import papers as papers_router
from api.routes import venues as venues_router
from services import mongo

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mongo.connect()
    yield
    await mongo.disconnect()


app = FastAPI(
    title="Paper Library",
    description="Self-hosted academic paper metadata and PDF reference store.",
    lifespan=lifespan,
)

app.include_router(health_router.router)
app.include_router(papers_router.router, prefix="/papers")
app.include_router(venues_router.router, prefix="/venues")

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/addvenue", include_in_schema=False)
async def page_addvenue():
    return FileResponse(_STATIC_DIR / "addvenue.html")


@app.get("/venues/ui", include_in_schema=False)
async def page_venues():
    return FileResponse(_STATIC_DIR / "venues.html")


@app.get("/conf", include_in_schema=False)
async def page_conf():
    return FileResponse(_STATIC_DIR / "conf.html")


@app.get("/journals", include_in_schema=False)
async def page_journals():
    return FileResponse(_STATIC_DIR / "journals.html")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")
