"""The Settings page, computed from one Snapshot: the profile's own settings and every source, read-only. Nothing
here writes anything, and nothing here shows a secret: a token's value and the environment it lives in never appear,
only the name of the variable that holds it — the shell's sidebar deliberately hides all of this
(`tests/test_server.py::test_the_shell_never_exposes_source_settings`); this page is the one place it is shown."""

from __future__ import annotations

import datetime as dt
import ntpath
from typing import Literal

from .. import __version__
from ..contract import CONTRACT_VERSION, Snapshot, Source
from ..profile import App, BenchmarkCfg, Profile, SourceCfg, You, source_config
from ..urls import shown_url
from ._base import View

# SourceCfg's own defaults, repeated here for a source row this profile no longer configures (a connector's own
# fabricated sub-source, such as the demo's fictional examples) and for a command or feed that leaves one out.
DEFAULT_STALE_AFTER = "36h"
DEFAULT_REFRESH = "1m"
DEFAULT_COMMAND_TIMEOUT = 30.0
DEFAULT_FEED_TIMEOUT = 5.0


class SourceRow(View):
    id: str
    label: str
    kind: str
    # a url without its query or fragment, a path as configured, "<program file name> <its arguments>" for a
    # command, or "" (demo)
    reads: str
    stale_after: str
    refresh: str | None = None  # only a command reuses its last answer
    timeout: float | None = None  # seconds; only a feed (url, path or command) times out
    token_env: str | None = None  # the variable's NAME; never its value
    status: Literal["ok", "stale", "error"]
    last_success: dt.datetime | None
    detail: str


class SettingsView(View):
    as_of: dt.datetime
    you: You
    app: App
    benchmark: BenchmarkCfg
    profile: str  # the file kestrel loaded, or "demo data"
    contract_version: str
    version: str
    sources: list[SourceRow]


def _program_display(command: list[str]) -> str:
    """The program's file name — never its folder, which can be a machine path — then its arguments, as configured.
    A path with no file name of its own (it ends in a slash: a folder, not a program) falls back to a plain word
    that could never be mistaken for a path — never the configured string itself, which would defeat the point."""
    name = ntpath.basename(command[0]) or "program"
    return " ".join([name, *command[1:]])


def _source_row(source: Source, cfg: SourceCfg | None) -> SourceRow:
    reads, refresh, timeout, token_env = "", None, None, None
    stale_after = cfg.stale_after if cfg is not None else DEFAULT_STALE_AFTER
    if cfg is not None:
        command = getattr(cfg, "command", None)
        url = getattr(cfg, "url", None)
        path = getattr(cfg, "path", None)
        if command:
            reads = _program_display(list(command))
            refresh = getattr(cfg, "refresh", None) or DEFAULT_REFRESH
            timeout = float(getattr(cfg, "timeout", None) or DEFAULT_COMMAND_TIMEOUT)
        elif url:
            try:
                reads = shown_url(url)  # never its query or fragment, where a key can hide
            except ValueError:  # the profile refuses such an address; if one got here, show nothing of it
                reads = ""
            token_env = getattr(cfg, "token_env", None)
            timeout = float(getattr(cfg, "timeout", None) or DEFAULT_FEED_TIMEOUT)
        elif path:
            reads = str(path)
            if cfg.kind == "feed":  # fdc and rails read a file too, but never time out: there is no network to wait on
                timeout = float(getattr(cfg, "timeout", None) or DEFAULT_FEED_TIMEOUT)
    return SourceRow(id=source.id, label=source.label, kind=source.kind, reads=reads, stale_after=stale_after,
                     refresh=refresh, timeout=timeout, token_env=token_env, status=source.status,
                     last_success=source.last_success, detail=source.detail)


def settings_view(snapshot: Snapshot, profile: Profile, now: dt.datetime, profile_origin: str) -> SettingsView:
    return SettingsView(
        as_of=now, you=profile.you, app=profile.app, benchmark=profile.benchmark, profile=profile_origin,
        contract_version=CONTRACT_VERSION, version=__version__,
        sources=[_source_row(s, source_config(profile, s.id)) for s in snapshot.sources],
    )
