"""The personal profile: who you are, how kestrel looks, and where your data comes from.

profile.toml is gitignored. It never holds secrets: a source names the environment variable that holds its key.
"""

from __future__ import annotations

import re
import tomllib
from datetime import timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class ProfileError(Exception):
    """A profile problem, worded so a person can fix it."""


_DURATION = re.compile(r"^\s*(\d+)\s*([mhd])\s*$")


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
    currency: str = "USD"
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


def load_profile(path: Path | None = None) -> tuple[Profile, str]:
    """Load a profile. With no path: ./profile.toml when it exists, else the built-in demo profile.

    Returns the profile and where it came from (for `kestrel check`).
    """
    if path is None:
        path = Path("profile.toml")
        if not path.exists():
            return DEMO_PROFILE, "built-in demo profile"
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ProfileError(f"{path}: file not found") from None
    except tomllib.TOMLDecodeError as exc:
        raise ProfileError(f"{path}: {exc}") from None
    try:
        return Profile.model_validate(raw), str(path)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors())
        raise ProfileError(f"{path}: {problems}") from None
