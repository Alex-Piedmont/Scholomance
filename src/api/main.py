"""FastAPI application for the tech transfer dashboard."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from ..database import db
from .routes import stats_router, technologies_router, opportunities_router

app = FastAPI(
    title="Tech Transfer Dashboard API",
    description="API for browsing university technology transfer listings",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(stats_router)
app.include_router(technologies_router)
app.include_router(opportunities_router)


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/health/db")
def db_health_check():
    """Database health check endpoint."""
    try:
        count = db.count_technologies()
        return {"status": "ok", "technologies_count": count}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# Static file serving for production
# Find the web/dist directory relative to this file
_current_dir = Path(__file__).parent
_project_root = _current_dir.parent.parent
_static_dir = _project_root / "web" / "dist"

if _static_dir.exists():
    # Mount static assets (JS, CSS, images)
    _assets_dir = _static_dir / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    # Serve index.html for SPA routing
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the SPA for all non-API routes."""
        # Don't serve index.html for API routes
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}

        # Check if requesting a specific file
        file_path = _static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # Return index.html for SPA routing
        index_path = _static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))

        return {"detail": "Not Found"}
