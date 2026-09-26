"""The read-only web server. GET routes only, bound to this computer (127.0.0.1)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .connectors import collect
from .contract import Money
from .profile import Profile
from .views.home import HomeView, home_view
from .views.shell import ShellView, shell_view
from .views.strategy import StrategiesView, StrategyView, strategies_view, strategy_view

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
LOCAL_HOSTS = ("127.0.0.1", "localhost")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _plain_parts(rest: str) -> tuple[str, ...] | None:
    """The path's parts when it is a plain relative path, else None.

    Decided on the text alone, before any filesystem call: on Windows a backslash or a drive colon could turn the
    path into a network (UNC) or absolute path, and merely resolving one of those reaches out over the network.
    A NUL character is refused too: the filesystem calls would raise on it.
    """
    if not rest or "\\" in rest or ":" in rest or chr(0) in rest or rest.startswith("/"):
        return None
    parts = PurePosixPath(rest).parts
    return None if ".." in parts else parts


def create_app(profile: Profile, *, clock: Callable[[], datetime] = _utcnow,
               web_dist: Path | None = WEB_DIST, allowed_hosts: Sequence[str] = LOCAL_HOSTS) -> FastAPI:
    app = FastAPI(title="kestrel", version=__version__, docs_url=None, redoc_url=None,
                  openapi_url="/api/openapi.json")
    # DNS-rebinding guard: a page elsewhere whose name resolves to 127.0.0.1 still sends its own Host header
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts))

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

    @app.get("/api/strategies", response_model=StrategiesView)
    def strategies() -> StrategiesView:
        now = clock()
        return strategies_view(collect(profile, now), profile, now)

    @app.get("/api/strategies/{strategy_id}", response_model=StrategyView)
    def strategy(strategy_id: str, book: Money = "real") -> StrategyView:
        now = clock()
        view = strategy_view(collect(profile, now), profile, now, strategy_id, book)
        if view is None:
            raise HTTPException(status_code=404, detail=f"no such strategy: {strategy_id}")
        return view

    @app.get("/api/{rest:path}", include_in_schema=False)
    def unknown_api(rest: str) -> None:
        raise HTTPException(status_code=404, detail=f"no such endpoint: /api/{rest}")

    if web_dist is not None and (web_dist / "index.html").is_file():
        root = web_dist.resolve()
        if (root / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

        @app.get("/{rest:path}", include_in_schema=False)
        def page(rest: str) -> FileResponse:
            parts = _plain_parts(rest)
            if parts:
                candidate = root.joinpath(*parts).resolve()
                if candidate.is_file() and root in candidate.parents:
                    return FileResponse(candidate)
            return FileResponse(root / "index.html")  # the app's router handles every other path

    return app
