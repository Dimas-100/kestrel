"""The read-only web server. GET routes only, bound to this computer (127.0.0.1)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .connectors import collect
from .profile import Profile
from .views.home import HomeView, home_view
from .views.shell import ShellView, shell_view

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_app(profile: Profile, *, clock: Callable[[], datetime] = _utcnow,
               web_dist: Path | None = WEB_DIST) -> FastAPI:
    app = FastAPI(title="kestrel", version=__version__, docs_url=None, redoc_url=None,
                  openapi_url="/api/openapi.json")

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"ok": True, "version": __version__}

    @app.get("/api/shell", response_model=ShellView)
    def shell() -> ShellView:
        now = clock()
        return shell_view(collect(profile, now), profile, now)

    @app.get("/api/home", response_model=HomeView)
    def home() -> HomeView:
        now = clock()
        return home_view(collect(profile, now), profile, now)

    @app.get("/api/{rest:path}", include_in_schema=False)
    def unknown_api(rest: str) -> None:
        raise HTTPException(status_code=404, detail=f"no such endpoint: /api/{rest}")

    if web_dist is not None and (web_dist / "index.html").is_file():
        root = web_dist.resolve()
        if (root / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @app.get("/{rest:path}", include_in_schema=False)
        def page(rest: str) -> FileResponse:
            candidate = (root / rest).resolve()
            if rest and candidate.is_file() and root in candidate.parents:
                return FileResponse(candidate)
            return FileResponse(root / "index.html")  # the app's router handles every other path

    return app
