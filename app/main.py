from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routes import auth as auth_routes
from app.routes import health as health_routes
from app.routes import workspaces as workspace_routes

logger = logging.getLogger("vibecast")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    logger.info("VibeCast backend starting in %s mode", settings.env)
    init_db()
    logger.info("Database initialized at %s", settings.db_path)
    yield
    logger.info("VibeCast backend shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VibeCast API",
        version="0.2.0",
        description="AI marketing team for B2B startups — multi-agent, workspace-native.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(workspace_routes.router)

    return app


app = create_app()
