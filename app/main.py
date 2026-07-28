from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.routers import connections, health, sync


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="Procore Intake Bridge",
    description="Private, read-only DMSA intake service. Phase A1 uses local fixtures only.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(connections.router)
app.include_router(sync.router)
