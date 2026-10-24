"""
N100 Financial Intelligence Platform
Day 38 - FastAPI Server Scaffold

Main FastAPI application.
"""

import logging
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = BASE_DIR / "database" / "n100.db"

API_VERSION = "1.0.0"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("n100-api")


# ============================================================
# DATABASE CONNECTION
# ============================================================


def get_db_connection():
    """
    Create and return a SQLite database connection.

    Row factory allows database rows to be accessed
    using column names.
    """

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="N100 Financial Intelligence Platform API",
    description=(
        "REST API for the N100 Financial Intelligence Platform. "
        "Provides access to company, financial, screening, "
        "sector, peer, valuation, portfolio and document modules."
    ),
    version=API_VERSION,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Invalid request parameter",
        },
    )


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Log HTTP method, path and response time for every request.
    """

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        return response

    finally:
        elapsed = time.perf_counter() - start_time

        logger.info(
            "%s %s | %.4f seconds",
            request.method,
            request.url.path,
            elapsed,
        )


# ============================================================
# ROUTERS
# ============================================================

API_PREFIX = "/api/v1"

app.include_router(
    companies.router,
    prefix=API_PREFIX,
)

app.include_router(
    screener.router,
    prefix=API_PREFIX,
)

app.include_router(
    sectors.router,
    prefix=API_PREFIX,
)

app.include_router(
    peers.router,
    prefix=API_PREFIX,
)

app.include_router(
    valuation.router,
    prefix=API_PREFIX,
)

app.include_router(
    portfolio.router,
    prefix=API_PREFIX,
)

app.include_router(
    documents.router,
    prefix=API_PREFIX,
)

app.include_router(
    health.router,
    prefix=API_PREFIX,
)


# ============================================================
# ROOT ENDPOINT
# ============================================================


@app.get("/")
def root():
    """
    API root endpoint.
    """

    return {
        "application": "N100 Financial Intelligence Platform",
        "status": "running",
        "version": API_VERSION,
        "docs": "/docs",
        "api_prefix": API_PREFIX,
    }


# ============================================================
# STARTUP MESSAGE
# ============================================================


@app.on_event("startup")
def startup_event():
    """
    Verify database availability when the API starts.
    """

    logger.info("=" * 70)
    logger.info("N100 FINANCIAL INTELLIGENCE PLATFORM API")
    logger.info("=" * 70)
    logger.info("Database: %s", DATABASE_PATH)

    if DATABASE_PATH.exists():
        logger.info("Database status: AVAILABLE")
    else:
        logger.error("Database status: NOT FOUND")


# ============================================================
# SHUTDOWN MESSAGE
# ============================================================


@app.on_event("shutdown")
def shutdown_event():
    logger.info("N100 API server stopped.")
