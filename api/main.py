from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from api.routes import health as health_router
from api.routes import papers as papers_router
from services import mongo


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


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")
