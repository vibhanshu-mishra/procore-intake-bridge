from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables
from app.routers import (
    connections,
    event_queue,
    health,
    polling,
    sync,
    sync_profiles,
    webhooks,
)


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
app.include_router(sync_profiles.router)
app.include_router(polling.router)
app.include_router(webhooks.router)
app.include_router(event_queue.router)
