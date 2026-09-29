"""What the app shell needs on every page: who you are, how it looks, and how fresh each source is."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from ..contract import Snapshot, Source
from ..logos import logo_files
from ..profile import App, Profile


class NavCounts(BaseModel):
    accounts: int
    books: int
    strategies: int


class ShellView(BaseModel):
    name: str
    app: App
    benchmark_label: str
    now: dt.datetime
    sources: list[Source]
    counts: NavCounts
    logos: list[str]  # the keys the logo route can serve; the app shows initials for the rest


def shell_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> ShellView:
    return ShellView(
        name=profile.you.name,
        app=profile.app,
        benchmark_label=profile.benchmark.label,
        now=now,
        sources=list(snapshot.sources),
        counts=NavCounts(accounts=len(snapshot.accounts), books=len(snapshot.books),
                         strategies=len(snapshot.strategies)),
        logos=sorted(logo_files(profile)),
    )
