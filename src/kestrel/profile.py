"""The personal profile: who you are, how kestrel looks, and where your data comes from.

profile.toml is gitignored. It never holds secrets: a source names the environment variable that holds its key.
"""

from __future__ import annotations

import re
import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Literal, get_args
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .contract import Category


class ProfileError(Exception):
    """A profile problem, worded so a person can fix it."""


_DURATION = re.compile(r"^\s*(\d+)\s*([mhd])\s*$")
# an environment variable's name in capitals: a token pasted in by mistake almost never looks like one
_ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")
_THIS_COMPUTER = ("127.0.0.1", "::1", "localhost")  # the hosts a token may go to over plain http


def parse_duration(text: str) -> timedelta:
    match = _DURATION.match(text)
    if not match:
        raise ValueError(f"not a duration: {text!r} (use a number and m, h or d, e.g. 15m, 36h, 2d)")
    amount, unit = int(match.group(1)), match.group(2)
    return {"m": timedelta(minutes=amount), "h": timedelta(hours=amount), "d": timedelta(days=amount)}[unit]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class You(_Strict):
    name: str = "there"


class App(_Strict):
    name: str = "kestrel"
    accent: Literal["rufous", "slate", "mono"] = "rufous"
    theme: Literal["system", "dark", "light"] = "system"
    gain_loss: Literal["green-red", "blue-orange"] = "green-red"
    density: Literal["comfortable", "compact"] = "comfortable"
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")  # an ISO 4217 code, e.g. USD, EUR
    timezone: str = "America/New_York"

    @field_validator("timezone")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"unknown time zone {value!r} (use an IANA name such as America/New_York)") from None
        return value


class BenchmarkCfg(_Strict):
    symbol: str = "SPY"
    label: str = "S&P 500"


class SourceCfg(BaseModel):
    # connector-specific keys (path, url, token_env, seed) are allowed and read by the connector
    model_config = ConfigDict(extra="allow", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,31}$")
    kind: str
    label: str = ""
    stale_after: str = "36h"

    @field_validator("stale_after")
    @classmethod
    def _duration(cls, value: str) -> str:
        parse_duration(value)
        return value

    @model_validator(mode="after")
    def _known_categories(self) -> SourceCfg:
        # a typo in a category must stop the profile: silently falling back would file the money under another heading
        categories = getattr(self, "categories", None)
        if categories is None:
            return self
        if not isinstance(categories, dict):
            raise ValueError("categories must be a table: account id or label = category")
        known = get_args(Category)
        for key, value in categories.items():
            if value not in known:
                raise ValueError(f"unknown category {value!r} for {key!r} (use {', '.join(known[:-1])} or {known[-1]})")
        return self

    @model_validator(mode="after")
    def _feed_shape(self) -> SourceCfg:
        # a feed's shape is checked when the profile loads, and no message repeats a value back: a url or a
        # token_env can hold a secret written in the wrong place
        if self.kind != "feed":
            return self
        url, path = getattr(self, "url", None), getattr(self, "path", None)
        if (url is None) == (path is None):
            raise ValueError('a feed source needs exactly one of url and path, e.g. url = '
                             '"http://127.0.0.1:8000/api/feed" or path = "../desk/feed.json"')
        if url is not None:
            if isinstance(url, str) and any(c.isspace() or not c.isprintable() for c in url):
                # urllib quietly drops tabs and line breaks, and http.client refuses a space with the path and
                # query (where a secret can hide) in its message
                raise ValueError("a feed url can't contain spaces or control characters (write a space as %20)")
            try:
                parts = urlsplit(url) if isinstance(url, str) else None
                # .port raises for a port that isn't a number or is out of range
                valid = (parts is not None and parts.scheme in ("http", "https") and bool(parts.hostname)
                         and parts.port != 0)
            except ValueError:  # that, or urlsplit("http://[::1/feed") with its own "Invalid IPv6 URL"
                valid = False
            if not valid:
                raise ValueError("a feed url must start with http:// or https:// and name a host "
                                 "(and a port from 1 to 65535, if it has one)")
            if parts.username is not None or parts.password is not None:
                raise ValueError("a feed url can't carry a user name or password: put the token in an environment "
                                 "variable and name it in token_env")
        elif not isinstance(path, str) or not path:
            raise ValueError('a feed path is a file name in quotes, e.g. path = "../desk/feed.json"')
        token_env = getattr(self, "token_env", None)
        if token_env is not None:
            if path is not None:
                raise ValueError("token_env goes with a url: a feed file is read without a token")
            if not isinstance(token_env, str) or not _ENV_NAME.match(token_env):
                raise ValueError("token_env is the name of an environment variable in capitals, such as "
                                 "KESTREL_DESK_TOKEN, never the token itself")
            if parts.scheme == "http" and parts.hostname not in _THIS_COMPUTER:
                # plain http shows the token to anything on the way; to this computer, nothing is on the way
                raise ValueError("a token goes only over https, or to this computer")
        timeout = getattr(self, "timeout", 5)
        if isinstance(timeout, bool) or not isinstance(timeout, int | float) or not 1 <= timeout <= 60:
            raise ValueError("timeout is in seconds, from 1 to 60")
        return self

    @property
    def stale_delta(self) -> timedelta:
        return parse_duration(self.stale_after)


def _demo_sources() -> list[SourceCfg]:
    return [SourceCfg(id="demo", kind="demo", label="Demo data")]


class Profile(_Strict):
    you: You = You()
    app: App = App()
    benchmark: BenchmarkCfg = BenchmarkCfg()
    sources: list[SourceCfg] = Field(default_factory=_demo_sources)

    @model_validator(mode="after")
    def _unique_source_ids(self) -> Profile:
        ids = [s.id for s in self.sources]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate source id(s): {', '.join(dupes)}")
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.app.timezone)


DEMO_PROFILE = Profile(you=You(name="Alex"))


def _resolve_paths(raw: dict, folder: Path) -> None:
    """A `path` in a source may start with ~ (your home folder); a relative one is relative to the profile's own
    folder, not to wherever kestrel was started."""
    sources = raw.get("sources")
    for i, source in enumerate(sources if isinstance(sources, list) else []):
        if isinstance(source, dict) and isinstance(source.get("path"), str):
            try:
                path = Path(source["path"]).expanduser()
            except RuntimeError:  # an unknown ~user, or no home folder to put in place of ~
                raise ValueError(f"sources.{i}: can't expand ~ in {source['path']!r} (write the full path)") from None
            source["path"] = str(path if path.is_absolute() else (folder / path).resolve())


def load_profile(path: Path | None = None) -> tuple[Profile, str]:
    """Load a profile. With no path: ./profile.toml when it exists, else the built-in demo profile.

    Returns the profile and where it came from (for `kestrel check`). Relative and ~ source paths come back absolute.
    """
    if path is None:
        path = Path("profile.toml")
        if not path.exists():
            return DEMO_PROFILE, "built-in demo profile"
    try:
        text = path.read_text(encoding="utf-8-sig")  # -sig: Windows editors often save a byte-order mark
    except FileNotFoundError:
        raise ProfileError(f"{path}: file not found") from None
    except UnicodeDecodeError:
        raise ProfileError(f"{path}: is not UTF-8 text (save it as UTF-8 and try again)") from None
    except OSError as exc:
        raise ProfileError(f"{path}: could not read the file ({exc.strerror or exc})") from None
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"{path}: {exc}") from None
    try:
        _resolve_paths(raw, path.parent)
    except ValueError as exc:
        raise ProfileError(f"{path}: {exc}") from None
    try:
        return Profile.model_validate(raw), str(path)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors())
        raise ProfileError(f"{path}: {problems}") from None
