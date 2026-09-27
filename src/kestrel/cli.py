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
from .profile import DEMO_PROFILE, Profile, ProfileError, load_profile

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


def _profile(args: argparse.Namespace) -> tuple[Profile, str]:
    """--demo shows the demo whatever profile.toml says; otherwise --profile, else ./profile.toml, else the demo."""
    if args.demo:
        return DEMO_PROFILE, "built-in demo profile"
    return load_profile(args.profile)


def _serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .server import WEB_DIST, create_app

    try:
        profile, origin = _profile(args)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    url = f"http://{HOST}:{args.port}"
    print(f"kestrel {url} - profile: {origin} - read-only - Ctrl+C to stop")
    if not (WEB_DIST / "index.html").is_file():
        print("web/dist is not built yet: run `npm ci && npm run build` in web/ (the API works without it)")
    if not args.no_open:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    # Settings shows which profile is in use: the file it was loaded from, or "demo data" when there wasn't one
    # (--demo, or no profile.toml at all) — never the "built-in demo profile" wording `check`'s banner line uses.
    settings_origin = "demo data" if profile is DEMO_PROFILE else origin
    uvicorn.run(create_app(profile, profile_origin=settings_origin), host=HOST, port=args.port, log_level="warning")
    return 0


def _check(args: argparse.Namespace) -> int:
    from .connectors import collect
    from .views.home import age_text

    try:
        profile, origin = _profile(args)
    except ProfileError as exc:
        print(f"profile problem: {exc}", file=sys.stderr)
        return 2
    now = datetime.now(timezone.utc)
    # UTF-8 out: a source's detail or an account's name can carry any character
    _emit(f"profile: {origin} - hello, {profile.you.name}")
    failed = False
    for cfg in profile.sources:
        # one source at a time, so each source's accounts print under it; never a balance
        part = collect(profile.model_copy(update={"sources": [cfg]}), now)
        for s in part.sources:
            age = f"{age_text(now - s.last_success)} ago" if s.last_success else "never"
            _emit(f"  {s.status:<5}  {s.label:<16} {s.kind:<16} {age}  {s.detail}".rstrip())
            failed = failed or s.status == "error"
        for a in part.accounts:
            _emit(f"{'':9}{a.id:<16} {a.category:<16} {a.name}")
    return 1 if failed else 0


def _demo(args: argparse.Namespace) -> int:
    from .connectors import collect
    from .views.accounts import account_view, accounts_view
    from .views.activity import activity_view
    from .views.backtests import backtests_view
    from .views.books import book_view, books_view
    from .views.calendar import calendar_view
    from .views.home import home_view
    from .views.settings import settings_view
    from .views.shell import shell_view
    from .views.strategy import strategies_view, strategy_view

    now = _now(args.now)
    snapshot = collect(DEMO_PROFILE, now)
    if args.view == "home":
        _emit(home_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "shell":
        _emit(shell_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "strategies":
        _emit(strategies_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "accounts":
        _emit(accounts_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "books":
        _emit(books_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "activity":
        _emit(activity_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "calendar":
        _emit(calendar_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "backtests":
        _emit(backtests_view(snapshot, DEMO_PROFILE, now).model_dump_json(indent=2))
    elif args.view == "settings":
        _emit(settings_view(snapshot, DEMO_PROFILE, now, "demo data").model_dump_json(indent=2))
    elif args.view in ("strategy", "account", "book"):
        if not args.id:
            example = {"strategy": "rsi2", "account": "roth", "book": "rsi2-real"}[args.view]
            print(f"--view {args.view} needs --id, e.g. --id {example}", file=sys.stderr)
            return 2
        view = (
            strategy_view(snapshot, DEMO_PROFILE, now, args.id, args.book) if args.view == "strategy"
            else account_view(snapshot, DEMO_PROFILE, now, args.id) if args.view == "account"
            else book_view(snapshot, DEMO_PROFILE, now, args.id)
        )
        if view is None:
            print(f"no {args.view} {args.id!r} in the demo data", file=sys.stderr)
            return 2
        _emit(view.model_dump_json(indent=2))
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
    serve.add_argument("--port", type=int, default=8030)
    serve.add_argument("--no-open", action="store_true", help="don't open a browser")
    serve.set_defaults(run=_serve)
    check = sub.add_parser("check", help="validate the profile and try every source")
    check.set_defaults(run=_check)
    for command in (serve, check):
        which = command.add_mutually_exclusive_group()
        which.add_argument("--profile", type=Path, help="profile file (default: ./profile.toml, else demo data)")
        which.add_argument("--demo", action="store_true", help="show the demo data, whatever profile.toml says")
    demo = sub.add_parser("demo", help="print the demo data as JSON (an example feed payload)")
    demo.add_argument("--view", choices=["snapshot", "home", "shell", "strategies", "strategy", "accounts", "account",
                                         "books", "book", "activity", "calendar", "backtests", "settings"],
                      default="snapshot")
    demo.add_argument("--id", help="the strategy, account or book the view shows, e.g. rsi2, roth or rsi2-real")
    demo.add_argument("--book", choices=["real", "paper"], default="real", help="the money --view strategy shows")
    demo.add_argument("--now", help="ISO time with offset, for reproducible output")
    demo.set_defaults(run=_demo)
    schema = sub.add_parser("schema", help="print the data contract as JSON Schema")
    schema.set_defaults(run=_schema)
    args = parser.parse_args(argv)
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
