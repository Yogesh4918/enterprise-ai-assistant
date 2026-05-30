"""CORS middleware configuration."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


def setup_cors(app: FastAPI) -> None:
    """Attach the CORS middleware to the FastAPI application.

    Reads allowed origins from settings. In debug mode every origin is
    accepted so local front-end dev servers work without friction.
    """
    settings = get_settings()

    origins: list[str] = settings.CORS_ORIGINS
    if settings.DEBUG:
        origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-Id",
            "X-Process-Time",
            "Content-Disposition",
        ],
        max_age=600,
    )
