from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.database import create_db_and_tables
from app.routers import (
    admin,
    attachments,
    connections,
    deployment,
    event_queue,
    health,
    onboarding,
    polling,
    sync,
    sync_profiles,
    webhooks,
)
from app.services.startup_checks import run_startup_checks


@asynccontextmanager
async def lifespan(_app: FastAPI):
    run_startup_checks(get_settings())
    create_db_and_tables()
    yield


app = FastAPI(
    title="Procore Intake Bridge",
    description="Private, read-only DMSA intake service. Phase A1 uses local fixtures only.",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(deployment.router)
app.include_router(connections.router)
app.include_router(sync.router)
app.include_router(sync_profiles.router)
app.include_router(polling.router)
app.include_router(webhooks.router)
app.include_router(event_queue.router)
app.include_router(attachments.router)
app.include_router(onboarding.router)
app.include_router(admin.router)
