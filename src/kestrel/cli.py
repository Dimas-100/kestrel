"""kestrel's command line: serve, check, demo, schema."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from .contract import Snapshot
from .profile import DEMO_PROFILE, ProfileError, load_profile

HOST = "127.0.0.1"  # never listen beyond this computer


def _emit(text: str) -> None:
    """Write UTF-8 whatever the console's code page is (redirected output on Windows is cp1252 otherwise)."""
    sys.stdout.buffer.write(text.encode("utf-8") + b"\n")
    sys.stdout.flush()


def _now(text: str | None) -> datetime:
    if not text:
        return datetime.now(timezone.utc)
    value = datetime.fromisoformat(text)
    if value.tzinfo is None:
        raise SystemExit("--now needs a time zone offset, e.g. 2026-09-25T21:08:00+00:00")
    return value


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .server import WEB_DIST, create_app

    try:
        profile, origin = load_profile(args.profile)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    url = f"http://{HOST}:{args.port}"
    print(f"kestrel {url} - profile: {origin} - read-only - Ctrl+C to stop")
    if not (WEB_DIST / "index.html").is_file():
        print("web/dist is not built yet: run `npm ci && npm run build` in web/ (the API works without it)")
    if not args.no_open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(profile), host=HOST, port=args.port, log_level="warning")
    return 0


def _check(args: argparse.Namespace) -> int:
    from .connectors import collect
    from .views.home import age_text

    try:
        profile, origin = load_profile(args.profile)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc)
    snapshot = collect(profile, now)
    print(f"profile: {origin} - hello, {profile.you.name}")
    for s in snapshot.sources:
        age = f"{age_text(now - s.last_success)} ago" if s.last_success else "never"
        print(f"  {s.status:<5}  {s.label:<16} {s.kind:<16} {age}  {s.detail}".rstrip())
    return 1 if any(s.status == "error" for s in snapshot.sources) else 0


def _demo(args: argparse.Namespace) -> int:
    from .connectors import collect
    from .views.home import home_view
    from .views.shell import shell_view

    now = _now(args.now)
    snapshot = collect(DEMO_PROFILE, now)
    if args.view == "home":
        _emit(home_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "shell":
        _emit(shell_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    else:
        _emit(snapshot.model_dump_json(indent=2))
    return 0


def _schema(args: argparse.Namespace) -> int:
    _emit(json.dumps(Snapshot.model_json_schema(), indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kestrel", description="A calm, read-only home for all your money.")
    sub = parser.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve", help="run the dashboard on this computer")
    serve.add_argument("--profile", type=Path, help="profile file (default: ./profile.toml, else demo data)")
    serve.add_argument("--port", type=int, default=8030)
    serve.add_argument("--no-open", action="store_true", help="don't open a browser")
    serve.set_defaults(run=_serve)
    check = sub.add_parser("check", help="validate the profile and try every source")
    check.add_argument("--profile", type=Path)
    check.set_defaults(run=_check)
    demo = sub.add_parser("demo", help="print the demo data as JSON (an example feed payload)")
    demo.add_argument("--view", choices=["snapshot", "home", "shell"], default="snapshot")
    demo.add_argument("--now", help="ISO time with offset, for reproducible output")
    demo.set_defaults(run=_demo)
    schema = sub.add_parser("schema", help="print the data contract as JSON Schema")
    schema.set_defaults(run=_schema)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
