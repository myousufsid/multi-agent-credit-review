"""
main.py — FastAPI application entry point (Stage 5).

Endpoints:
  GET /health      — liveness check
  GET /review/demo — runs the full Supervisor Agent workflow on the
                     Greenfield Supplies fictional fixtures and returns
                     the complete underwriting preparation report.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.supervisor_agent import run_supervisor_review

app = FastAPI(
    title="Multi-Agent Credit Review API",
    description=(
        "Prepares underwriting information for human review. "
        "This system never independently approves or rejects credit."
    ),
    version="0.5.0",
)

# ---------------------------------------------------------------------------
# CORS — allow the frontend (opened as a local file or on any localhost port)
# to call the API from the browser.  Starlette ships with FastAPI so this
# requires no new dependency.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev-only: accepts file:// and any localhost origin
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Paths to the sample fixture files.
# Resolved relative to this source file so they work regardless of the
# working directory from which uvicorn is launched.
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent / "data"
_SAMPLE_BUSINESS_PATH = _DATA_DIR / "sample_business.json"
_SAMPLE_DOCUMENTS_PATH = _DATA_DIR / "sample_documents.json"


def _decimal_serializer(obj: Any) -> Any:
    """
    JSON serializer for objects not serializable by the standard json module.

    Decimal values are serialized as strings to preserve full precision and
    avoid floating-point rounding errors (e.g. Decimal("90.67") → "90.67").
    """
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _safe_jsonable(data: Any) -> Any:
    """
    Recursively walk a nested structure and convert Decimal values to strings.

    FastAPI's default JSON encoder does not handle Decimal. We convert the
    entire result dict to a plain-Python structure before returning it, so
    that FastAPI can serialize it without custom encoder configuration.
    """
    if isinstance(data, dict):
        return {k: _safe_jsonable(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_safe_jsonable(item) for item in data]
    if isinstance(data, Decimal):
        return str(data)
    return data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["ops"])
def health_check() -> dict:
    """Return a simple liveness status for the service."""
    return {"status": "ok", "service": "credit-review-api", "stage": 5}


@app.get("/review/demo", tags=["review"])
def review_demo() -> JSONResponse:
    """
    Run the full multi-agent credit review workflow on the Greenfield Supplies
    fictional sample data and return the complete underwriting preparation report.

    This endpoint exists for demonstration and development purposes. It uses
    fictional data only and must never be used to make real lending decisions.
    """
    business_data = json.loads(_SAMPLE_BUSINESS_PATH.read_text(encoding="utf-8"))
    document_data = json.loads(_SAMPLE_DOCUMENTS_PATH.read_text(encoding="utf-8"))

    result = run_supervisor_review(business_data, document_data)

    # Convert Decimal values to strings throughout the nested result so the
    # response serializes cleanly without precision loss.
    serializable_result = _safe_jsonable(result)

    return JSONResponse(content=serializable_result)
