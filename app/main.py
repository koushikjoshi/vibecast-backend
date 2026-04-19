from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import episodes, feed, health, hosts, runs, traces

logger = logging.getLogger("vibecast")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    logger.info("VibeCast backend starting in %s mode", settings.env)
    yield
    logger.info("VibeCast backend shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VibeCast API",
        version="0.1.0",
        description="Newsroom-as-a-service backend.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(episodes.router, prefix="/api/episodes", tags=["episodes"])
    app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
    app.include_router(hosts.router, prefix="/api/hosts", tags=["hosts"])
    app.include_router(traces.router, prefix="/api/traces", tags=["traces"])
    app.include_router(feed.router, tags=["feed"])

    return app


app = create_app()
