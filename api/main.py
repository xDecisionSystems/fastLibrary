from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from api.routes import health as health_router
from api.routes import papers as papers_router
from api.routes import strategies as strategies_router
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

app.include_router(papers_router.router, prefix="/papers")
app.include_router(health_router.router)
app.include_router(papers_router.router, prefix="/api/papers")
app.include_router(venues_router.router, prefix="/api/venues")
app.include_router(strategies_router.router, prefix="/api/strategies")

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/papers-ui", include_in_schema=False)
async def page_papers():
    return FileResponse(_STATIC_DIR / "papers.html")


@app.get("/addconf", include_in_schema=False)
async def page_addconf():
    return FileResponse(_STATIC_DIR / "addconf.html")


@app.get("/addjournal", include_in_schema=False)
async def page_addjournal():
    return FileResponse(_STATIC_DIR / "addjournal.html")


@app.get("/venues", include_in_schema=False)
async def page_venues():
    return FileResponse(_STATIC_DIR / "venues.html")


@app.get("/conferences", include_in_schema=False)
async def page_conferences():
    return FileResponse(_STATIC_DIR / "conf.html")


@app.get("/journals", include_in_schema=False)
async def page_journals():
    return FileResponse(_STATIC_DIR / "journals.html")


@app.get("/tags", include_in_schema=False)
async def page_tags():
    return FileResponse(_STATIC_DIR / "tags.html")


@app.get("/venues/{slug}", include_in_schema=False)
async def page_venue(slug: str):
    return FileResponse(_STATIC_DIR / "venue.html")


@app.get("/getpapers/{slug}", include_in_schema=False)
async def page_getpapers_redirect(slug: str):
    return RedirectResponse(url=f"/venues/{slug}", status_code=301)


@app.get("/strategies", include_in_schema=False)
async def page_strategies():
    return FileResponse(_STATIC_DIR / "strategies.html")


@app.get("/strategies/{slug}", include_in_schema=False)
async def page_strategy(slug: str):
    return FileResponse(_STATIC_DIR / "strategy.html")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/venues")
