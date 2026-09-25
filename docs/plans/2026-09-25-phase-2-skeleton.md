# Phase 2 — the skeleton — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `kestrel serve` opens a working, read-only Home page on demo data: net worth, allocation, trading vs index money, what needs you, every book, today's runs and open positions. It sits inside the Graphite shell (greeting, grouped navigation, source freshness, light and dark themes, phone layout).

**Architecture:**
- **Python package `kestrel`:**
  - a pydantic data contract (`Snapshot`),
  - a profile loader,
  - connectors (only `demo` in this phase) merged by `collect()`,
  - pure view builders (`home_view`, `shell_view`),
  - a FastAPI server with GET routes only, which also serves the built web app,
  - a small CLI.
- **The web app (`web/`):**
  - React + TypeScript + Vite + Tailwind v4 with TanStack Router and Query,
  - the Graphite tokens from `docs/design-system.md`,
  - one in-house line chart on d3-scale/d3-shape.
- **Cross-boundary check:** Python generates the web test fixtures, and a Python test fails when they drift, so the two halves can't silently disagree.

**Tech Stack:** Python ≥ 3.11, FastAPI ≥ 0.136, pydantic ≥ 2.13, uvicorn ≥ 0.49, tzdata, pytest, ruff. Node 24, React 19.2, Vite 8, Tailwind 4.3, TanStack Router 1.170 / Query 5, d3-scale 4 / d3-shape 3 / d3-array 3, Vitest 4.1 + Testing Library 16 + jsdom 27, TypeScript ~6.0, @fontsource Geist + Geist Mono.

**Spec:** `docs/specs/2026-09-25-kestrel-design.md` (with `docs/design-system.md` for every visual value).

**Provenance:** every code block below was run in a scratch clone of this repo before the plan was written:
- `pytest`: 71 passed; `ruff check .` clean.
- `npm test`: 35 passed; `tsc --noEmit` clean; `npm run build` succeeded.
- `kestrel serve` was screenshotted at 390, 768, 1024 and 1440 px in both themes, with no panel overflow and no sideways page scroll.

Type it in as written. If something doesn't match, stop and report it rather than improvising.

## Global Constraints

- **Read-only, always.**
  - GET routes only; the server binds `127.0.0.1` only.
  - No import of any broker or trading library, and no call named `place`, `place_order`, `submit_order`, `cancel`, `cancel_order`, `replace_order` or `modify_order`, anywhere in `src/kestrel`.
- **Nothing private in git.**
  - Demo data is fictional ("Alex").
  - `profile.toml`, `.env*`, `data/`, `web/dist/` and `node_modules/` stay ignored.
  - `tests/test_hygiene.py` must keep passing on every commit.
- **Design system is law.**
  - Components use the tokens in `web/src/styles/tokens.css` and never raw hex (a test enforces this).
  - Real is solid, paper is hatched (dashed for lines), expected is dotted.
  - A gain or loss always carries a sign and ▲/▼.
- **Copy rules:**
  - True minus sign (−).
  - Em dash (—) for a missing value.
  - Sentence case.
  - 24-hour times in the profile's time zone.
- **Python ≥ 3.11.** On Windows, the tools live in `.venv/Scripts/`; on macOS and Linux, in `.venv/bin/`. Commands below use `.venv/Scripts/…`.
- **CLI output** is ASCII for human lines; JSON goes out as UTF-8 bytes whatever the console code page is.
- **Default port** `8030`. The Vite dev server proxies `/api` to it.
- **Commit style:** `feat(scope): …` / `test(scope): …` / `docs: …`, each ending with the `Co-Authored-By` trailer given in the session.

## Review Focus

These are the inputs most likely to bite a real person that the happy path never meets. Each has a test in the task named after it.

- **Early January.** "Year to date" has fewer than 5 points. The comparison falls back to the past 12 months and says so. Test: `test_early_january_falls_back_to_twelve_months` (Task 5).
- **A source that fails or doesn't exist yet.** A misspelled `kind`, or a Phase 4 connector named early. The page still renders, the source shows `error`, and Needs you gets a warning. Tests: `test_collect_marks_an_unknown_connector_as_an_error_and_keeps_going` (Task 4), `test_an_error_source_becomes_a_warning` (Task 5), `test_check_fails_when_a_source_cannot_be_read` (Task 7).
- **Timestamps in different offsets.** Run times arrive as `-04:00`, "now" as `Z`. The *now* line must compare instants, not strings. Test: `puts the now line between done and due runs` (Task 10, against the generated fixture, which mixes both).
- **A currency other than USD.** A profile with `currency = "EUR"` formats every amount in euros. Test: `in another currency > follows the profile` (Task 8).
- **Phone widths.** No sideways page scroll. Screen-reader labels inside scrolling tables must not escape their scroll box. Test: `keeps screen-reader labels inside scrolling tables` (Task 8), plus the screenshot pass in Task 11.

## File map

```
pyproject.toml                        package, deps, `kestrel` script (replaces the Phase 1 tools-only file)
profile.example.toml                  demo profile (committed); later-phase sources commented out
src/kestrel/
  __init__.py                         version
  contract.py                         Snapshot and its parts; merge()
  metrics.py                          growth_index, max_drawdown_pct, expected_band, largest_remainder, sum_series
  profile.py                          Profile, load_profile, ProfileError, DEMO_PROFILE, parse_duration
  connectors/__init__.py              build(), collect()
  connectors/base.py                  Connector protocol, ConnectorUnavailable
  connectors/demo.py                  DemoConnector (seed 340), weekdays_ending
  views/__init__.py
  views/home.py                       HomeView and home_view(); age_text()
  views/shell.py                      ShellView and shell_view()
  server.py                           create_app(), WEB_DIST
  cli.py                              serve · check · demo · schema
docs/data-contract.md                 the format any source speaks
docs/contract/snapshot.schema.json    generated by `kestrel schema`
tests/test_{contract,metrics,profile,demo_connector,home_view,server,read_only_guard,cli,generated_files}.py
web/                                  package.json, index.html, vite.config.ts, tsconfig.json, public/favicon.svg
web/src/main.tsx · router.tsx
web/src/styles/tokens.css · design.test.ts
web/src/lib/api.ts · format.ts · greeting.ts · theme.ts (+ tests)
web/src/components/Icon.tsx · bits.tsx
web/src/shell/Shell.tsx (+ test)
web/src/charts/geometry.ts (+ test) · LineChart.tsx
web/src/pages/Soon.tsx · pages/home/*.tsx (+ Home.test.tsx)
web/src/test/setup.ts · renderApp.tsx · fixtures/{home,shell}.json (generated)
.github/workflows/ci.yml
```

---

### Task 1: Package and data contract

**Files:**
- Modify: `pyproject.toml` (replace the whole file)
- Create: `src/kestrel/__init__.py`, `src/kestrel/contract.py`
- Test: `tests/test_contract.py`

**Interfaces:**
- Produces:
  - `kestrel.contract`: `CONTRACT_VERSION = "1"`; frozen pydantic models `Source`, `Account`, `Holding`, `ValuePoint(date, value, net_flow=0.0)`, `Series(id, points)`, `Step`, `Expected`, `Strategy`, `Book`, `Position`, `Trade`, `Run`, `Alert`, `Benchmark`, `Snapshot`.
  - `merge(snapshots: list[Snapshot], generated_at: datetime) -> Snapshot`.
  - Type aliases `Money = Literal["real","paper"]` and `Category = Literal["long_term","trading","cash","other"]`.

- [ ] **Step 1: Make the repo a package and install it**

`pyproject.toml`:

````toml
[build-system]
requires = ["setuptools>=77"]
build-backend = "setuptools.build_meta"

[project]
name = "kestrel"
version = "0.1.0"
description = "A calm, read-only home for all your money."
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.136",
  "pydantic>=2.13",
  "uvicorn>=0.49",
  "tzdata>=2024.1",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.5", "httpx>=0.28"]

[project.scripts]
kestrel = "kestrel.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I"]
````

`src/kestrel/__init__.py`:

````python
"""kestrel: a calm, read-only home for all your money."""

__version__ = "0.1.0"
````


Run: `.venv/Scripts/python -m pip install -e ".[dev]"`
Expected: `Successfully installed … kestrel-0.1.0 …`. The existing `tests/test_hygiene.py` still passes (`.venv/Scripts/python -m pytest -q`).

- [ ] **Step 2: Write the failing tests**

`tests/test_contract.py`:

````python
import datetime as dt

import pytest
from pydantic import ValidationError

from kestrel.contract import CONTRACT_VERSION, Snapshot, ValuePoint, merge

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


def minimal(**extra):
    return {"contract_version": "1", "generated_at": NOW.isoformat(), **extra}


def test_a_minimal_snapshot_loads_with_empty_lists():
    snap = Snapshot.model_validate(minimal())
    assert snap.contract_version == CONTRACT_VERSION
    assert snap.accounts == [] and snap.benchmark is None


def test_an_unknown_major_version_is_refused_with_a_reason():
    with pytest.raises(ValidationError, match="unsupported contract version '2'"):
        Snapshot.model_validate(minimal(contract_version="2"))


def test_a_newer_minor_version_and_unknown_fields_still_load():
    snap = Snapshot.model_validate(minimal(contract_version="1.3", something_new={"x": 1}))
    assert snap.contract_version == "1.3"


def test_timestamps_must_carry_an_offset():
    with pytest.raises(ValidationError):
        Snapshot.model_validate({"generated_at": "2026-09-25T21:08:00"})


def test_a_full_account_and_series_round_trip_through_json():
    snap = Snapshot.model_validate(minimal(
        accounts=[{"id": "roth", "name": "Roth IRA", "category": "long_term", "value": 100.0,
                   "as_of": NOW.isoformat()}],
        account_history=[{"id": "roth", "points": [{"date": "2026-09-24", "value": 99.0},
                                                    {"date": "2026-09-25", "value": 100.0, "net_flow": 0.5}]}],
    ))
    again = Snapshot.model_validate_json(snap.model_dump_json())
    assert again == snap
    assert again.account_history[0].points[1] == ValuePoint(date=dt.date(2026, 9, 25), value=100.0, net_flow=0.5)


def test_an_unknown_category_is_refused():
    with pytest.raises(ValidationError):
        Snapshot.model_validate(minimal(accounts=[{"id": "x", "name": "X", "category": "crypto", "value": 1,
                                                   "as_of": NOW.isoformat()}]))


def test_merge_concatenates_lists_and_keeps_the_first_benchmark():
    bench = {"symbol": "SPY", "label": "S&P 500", "points": [{"date": "2026-09-25", "value": 600.0}]}
    a = Snapshot.model_validate(minimal(sources=[{"id": "a", "label": "A", "kind": "demo"}], benchmark=bench))
    b = Snapshot.model_validate(minimal(sources=[{"id": "b", "label": "B", "kind": "feed"}]))
    merged = merge([a, b], generated_at=NOW)
    assert [s.id for s in merged.sources] == ["a", "b"]
    assert merged.benchmark is not None and merged.benchmark.symbol == "SPY"
    assert merge([], generated_at=NOW).sources == []
````


- [ ] **Step 3: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_contract.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'kestrel.contract'`.

- [ ] **Step 4: Implement the contract**

`src/kestrel/contract.py`:

````python
"""The kestrel data contract, version 1.

Every connector returns a Snapshot. A private system plugs in by serving a Snapshot as JSON (the feed connector).
Within a major version changes are additive only, so unknown fields are ignored and a newer minor still loads.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator

CONTRACT_VERSION = "1"

Money = Literal["real", "paper"]
Category = Literal["long_term", "trading", "cash", "other"]


class Model(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class Source(Model):
    id: str
    label: str
    kind: str
    last_success: AwareDatetime | None = None
    status: Literal["ok", "stale", "error"] = "ok"
    detail: str = ""


class Account(Model):
    id: str
    name: str
    institution: str = ""
    category: Category
    value: float
    cash: float = 0.0
    as_of: AwareDatetime


class Holding(Model):
    account_id: str
    symbol: str
    name: str = ""
    quantity: float
    price: float
    value: float
    cost_basis: float | None = None


class ValuePoint(Model):
    date: dt.date
    value: float
    net_flow: float = 0.0  # deposits minus withdrawals on that day


class Series(Model):
    id: str  # the account id or book id the points belong to
    points: list[ValuePoint]


class Step(Model):
    label: str  # "Universe", "Entry", "Protect", "Exit"
    title: str
    text: str
    params: list[str] = []


class Expected(Model):
    win_rate: float  # percent, 0..100
    avg_trade_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    trades_per_month: float
    sd_trade_pct: float
    distribution: list[float] = []  # share of trades (%) in each 1-point bucket from -10% to +10%
    source: str = ""
    window: str = ""


class Strategy(Model):
    id: str
    name: str
    summary: str = ""
    steps: list[Step] = []
    sizing: str = ""
    expected: Expected | None = None
    review_at_trades: int | None = None


class Book(Model):
    id: str
    name: str
    money: Money
    strategy_id: str
    account_id: str | None = None
    status: Literal["running", "paused", "parked"]
    started: dt.date
    value: float
    slots_total: int | None = None
    next_run: AwareDatetime | None = None


class Position(Model):
    book_id: str
    symbol: str
    quantity: float
    entry_price: float
    last_price: float
    stop_price: float | None = None
    opened: dt.date
    note: str = ""


class Trade(Model):
    book_id: str
    symbol: str
    opened: dt.date
    closed: dt.date
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float
    r_multiple: float | None = None
    exit_reason: str = ""


class Run(Model):
    time: AwareDatetime
    label: str
    book_id: str | None = None
    status: Literal["done", "due", "late", "failed", "paused"]
    detail: str = ""


class Alert(Model):
    level: Literal["serious", "warning", "note"]
    title: str
    detail: str = ""
    link: str = ""


class Benchmark(Model):
    symbol: str
    label: str
    points: list[ValuePoint]  # value = the close


class Snapshot(Model):
    contract_version: str = CONTRACT_VERSION
    generated_at: AwareDatetime
    sources: list[Source] = []
    accounts: list[Account] = []
    holdings: list[Holding] = []
    account_history: list[Series] = []
    books: list[Book] = []
    book_history: list[Series] = []
    positions: list[Position] = []
    trades: list[Trade] = []
    strategies: list[Strategy] = []
    runs: list[Run] = []
    alerts: list[Alert] = []
    benchmark: Benchmark | None = None

    @field_validator("contract_version")
    @classmethod
    def _same_major(cls, value: str) -> str:
        if value.split(".")[0] != CONTRACT_VERSION:
            raise ValueError(
                f"unsupported contract version {value!r}; this kestrel reads major version {CONTRACT_VERSION}"
            )
        return value


_LIST_FIELDS = (
    "sources", "accounts", "holdings", "account_history", "books", "book_history",
    "positions", "trades", "strategies", "runs", "alerts",
)


def merge(snapshots: list[Snapshot], generated_at: dt.datetime) -> Snapshot:
    """Combine the snapshots of several connectors into one. The first benchmark found wins."""
    fields: dict[str, object] = {name: [item for s in snapshots for item in getattr(s, name)] for name in _LIST_FIELDS}
    fields["benchmark"] = next((s.benchmark for s in snapshots if s.benchmark is not None), None)
    return Snapshot(generated_at=generated_at, **fields)
````


- [ ] **Step 5: Run the tests and watch them pass**

Run: `.venv/Scripts/python -m pytest tests/test_contract.py -q && .venv/Scripts/python -m ruff check .`
Expected: `7 passed`; `All checks passed!`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/kestrel/__init__.py src/kestrel/contract.py tests/test_contract.py
git commit -m "feat(contract): the kestrel data contract v1 (Snapshot) and merge"
```

---

### Task 2: Money math

**Files:**
- Create: `src/kestrel/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Consumes: `ValuePoint` (Task 1).
- Produces:
  - `growth_index(points) -> list[float]` (time-weighted, starts at 1.0, net of `net_flow`)
  - `max_drawdown_pct(index) -> float` (≤ 0)
  - `expected_band(avg, sd, n) -> (lo, hi)` (95%: ±1.96·sd/√n; `ValueError` when n ≤ 0)
  - `largest_remainder(shares, total=100) -> list[int]`
  - `sum_series(series) -> list[ValuePoint]` (carries missing days forward; a late series' opening value counts as a flow)

- [ ] **Step 1: Write the failing tests**

`tests/test_metrics.py`:

````python
import datetime as dt

import pytest

from kestrel.contract import ValuePoint
from kestrel.metrics import expected_band, growth_index, largest_remainder, max_drawdown_pct, sum_series


def vp(day, value, flow=0.0):
    return ValuePoint(date=dt.date(2026, 9, day), value=value, net_flow=flow)


def test_growth_index_ignores_deposits():
    # 100 -> 110 of which 10 was a deposit: no performance at all
    assert growth_index([vp(1, 100), vp(2, 110, 10)]) == [1.0, 1.0]


def test_growth_index_chains_daily_returns():
    index = growth_index([vp(1, 100), vp(2, 110), vp(3, 99)])
    assert index == pytest.approx([1.0, 1.1, 0.99])


def test_growth_index_survives_a_zero_balance_and_empty_input():
    assert growth_index([]) == []
    assert growth_index([vp(1, 0), vp(2, 50, 50)]) == [1.0, 1.0]


def test_max_drawdown_is_the_worst_fall_from_a_peak():
    assert max_drawdown_pct([1.0, 1.2, 0.9, 1.3, 1.17]) == pytest.approx(-25.0)
    assert max_drawdown_pct([1.0, 1.1, 1.2]) == 0.0


def test_expected_band_narrows_with_more_trades():
    lo4, hi4 = expected_band(0.84, 3.0, 4)
    lo100, hi100 = expected_band(0.84, 3.0, 100)
    assert (lo4, hi4) == pytest.approx((0.84 - 2.94, 0.84 + 2.94))
    assert hi100 - lo100 < hi4 - lo4
    with pytest.raises(ValueError):
        expected_band(0.84, 3.0, 0)


def test_largest_remainder_always_totals_exactly():
    assert largest_remainder([71.53, 12.40, 16.07]) == [72, 12, 16]
    assert sum(largest_remainder([1, 1, 1])) == 100
    assert largest_remainder([0, 0]) == [0, 0]


def test_sum_series_carries_forward_a_missing_day():
    a = [vp(1, 100), vp(2, 101), vp(3, 102)]
    b = [vp(1, 50), vp(3, 55)]  # no point on the 2nd
    assert [p.value for p in sum_series([a, b])] == [150, 151, 157]


def test_sum_series_counts_a_late_account_as_a_deposit_not_growth():
    a = [vp(1, 100), vp(2, 100)]
    late = [vp(2, 40)]
    total = sum_series([a, late])
    assert total[1].value == 140 and total[1].net_flow == 40
    assert growth_index(total) == [1.0, 1.0]
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_metrics.py -q`
Expected: `ModuleNotFoundError: No module named 'kestrel.metrics'`.

- [ ] **Step 3: Implement**

`src/kestrel/metrics.py`:

````python
"""Pure money math shared by every view. No I/O, no clock."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .contract import ValuePoint


def growth_index(points: Sequence[ValuePoint]) -> list[float]:
    """Time-weighted growth index starting at 1.0.

    Each step is the day's change net of that day's deposits and withdrawals, so adding money never
    looks like performance.
    """
    if not points:
        return []
    index = [1.0]
    for prev, cur in zip(points, points[1:]):
        step = (cur.value - cur.net_flow) / prev.value if prev.value > 0 else 1.0
        index.append(index[-1] * step)
    return index


def max_drawdown_pct(index: Sequence[float]) -> float:
    """Worst fall from a running peak, as a negative percent (0.0 when it never fell)."""
    peak = -math.inf
    worst = 0.0
    for value in index:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, value / peak - 1.0)
    return worst * 100.0


def expected_band(avg: float, sd: float, n: int) -> tuple[float, float]:
    """95% range for the average of n trades: avg ± 1.96·sd/√n."""
    if n <= 0:
        raise ValueError("n must be positive")
    half = 1.96 * sd / math.sqrt(n)
    return avg - half, avg + half


def largest_remainder(shares: Sequence[float], total: int = 100) -> list[int]:
    """Round shares to whole units that add up to exactly `total` (for the 100-cell waffle)."""
    whole = sum(shares)
    if whole <= 0:
        return [0] * len(shares)
    raw = [s / whole * total for s in shares]
    floors = [math.floor(r) for r in raw]
    left = total - sum(floors)
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in by_remainder[:left]:
        floors[i] += 1
    return floors


def sum_series(series: Sequence[Sequence[ValuePoint]]) -> list[ValuePoint]:
    """Add value series by date.

    A series with no point on a date contributes its last known value. A series that appears after the
    first date brings its opening value in as a flow, so a newly linked account is not counted as growth.
    """
    dates = sorted({p.date for s in series for p in s})
    by_date = [{p.date: p for p in s} for s in series]
    last: list[float | None] = [None] * len(series)
    out: list[ValuePoint] = []
    for n, day in enumerate(dates):
        total = 0.0
        flow = 0.0
        for i, points in enumerate(by_date):
            point = points.get(day)
            if point is not None:
                if last[i] is None and n > 0:
                    flow += point.value
                else:
                    flow += point.net_flow
                last[i] = point.value
            if last[i] is not None:
                total += last[i]
        out.append(ValuePoint(date=day, value=round(total, 2), net_flow=round(flow, 2)))
    return out
````


- [ ] **Step 4: Run them and watch them pass**

Run: `.venv/Scripts/python -m pytest tests/test_metrics.py -q`
Expected: `8 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/metrics.py tests/test_metrics.py
git commit -m "feat(metrics): growth index net of deposits, drawdown, expected band, waffle rounding, series sum"
```

---

### Task 3: The profile

**Files:**
- Create: `src/kestrel/profile.py`, `profile.example.toml`
- Test: `tests/test_profile.py`

**Interfaces:**
- Produces:
  - `Profile(you, app, benchmark, sources)` with `.tz: ZoneInfo`, and `App` (name, accent, theme, gain_loss, density, currency, timezone).
  - `SourceCfg(id, kind, label, stale_after)`, with extra keys allowed and a `.stale_delta` property.
  - `DEMO_PROFILE` (name "Alex", one `demo` source).
  - `load_profile(path: Path | None) -> tuple[Profile, str]`, which raises `ProfileError` with a message naming the field.
  - `parse_duration("15m" | "36h" | "2d") -> timedelta`.

- [ ] **Step 1: Write the example profile and the failing tests**

`profile.example.toml`:

````toml
# kestrel profile. Copy this file to profile.toml (gitignored) and make it yours.
# Never put a key or password in here: a source names the environment variable that holds it.

[you]
name = "Alex"

[app]
name = "kestrel"
accent = "rufous"          # rufous | slate | mono
theme = "system"           # system | dark | light
gain_loss = "green-red"    # green-red | blue-orange
density = "comfortable"    # comfortable | compact
currency = "USD"
timezone = "America/New_York"

[benchmark]
symbol = "SPY"
label = "S&P 500"

# Where your data comes from. The demo source works out of the box.
[[sources]]
id = "demo"
kind = "demo"
label = "Demo data"

# Coming in a later version (Phase 4):
#
# [[sources]]
# id = "portfolio"
# kind = "fdc"                       # financial-data-collector's SQLite warehouse, read-only
# path = "../financial-data-collector/data/warehouse.db"
# stale_after = "36h"
#
# [[sources]]
# id = "paper"
# kind = "rails"                     # a trading-rails install: paper state, run log, backtests
# path = "../trading-rails/data"
#
# [[sources]]
# id = "desk"
# kind = "feed"                      # any system that serves the kestrel contract as JSON
# url = "http://127.0.0.1:8000/api/feed"
# token_env = "KESTREL_DESK_TOKEN"
# stale_after = "15m"
````

`tests/test_profile.py`:

````python
from datetime import timedelta
from pathlib import Path

import pytest

from kestrel.profile import DEMO_PROFILE, ProfileError, load_profile, parse_duration

ROOT = Path(__file__).resolve().parents[1]


def write(tmp_path, text):
    path = tmp_path / "profile.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_the_committed_example_profile_loads():
    profile, origin = load_profile(ROOT / "profile.example.toml")
    assert profile.you.name == "Alex"
    assert [s.kind for s in profile.sources] == ["demo"]
    assert origin.endswith("profile.example.toml")


def test_no_profile_file_means_the_demo_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    profile, origin = load_profile()
    assert profile == DEMO_PROFILE and origin == "built-in demo profile"


def test_a_profile_in_the_working_directory_is_used(tmp_path, monkeypatch):
    write(tmp_path, '[you]\nname = "Sam"\n')
    monkeypatch.chdir(tmp_path)
    profile, _ = load_profile()
    assert profile.you.name == "Sam"
    assert profile.sources[0].kind == "demo"  # sources default to demo data


def test_a_bad_setting_names_the_field(tmp_path):
    with pytest.raises(ProfileError, match=r"app\.accent"):
        load_profile(write(tmp_path, '[app]\naccent = "purple"\n'))


def test_a_typo_in_a_section_is_refused(tmp_path):
    with pytest.raises(ProfileError, match="nmae"):
        load_profile(write(tmp_path, '[you]\nnmae = "Sam"\n'))


def test_broken_toml_is_reported_with_the_path(tmp_path):
    with pytest.raises(ProfileError, match="profile.toml"):
        load_profile(write(tmp_path, "[you\nname = 1\n"))


def test_a_missing_explicit_path_is_reported(tmp_path):
    with pytest.raises(ProfileError, match="file not found"):
        load_profile(tmp_path / "nope.toml")


def test_an_unknown_time_zone_is_refused(tmp_path):
    with pytest.raises(ProfileError, match="unknown time zone"):
        load_profile(write(tmp_path, '[app]\ntimezone = "Mars/Olympus"\n'))


def test_duplicate_source_ids_are_refused(tmp_path):
    text = '[[sources]]\nid = "a"\nkind = "demo"\n[[sources]]\nid = "a"\nkind = "demo"\n'
    with pytest.raises(ProfileError, match="duplicate source id"):
        load_profile(write(tmp_path, text))


def test_connector_specific_keys_are_kept_for_the_connector(tmp_path):
    profile, _ = load_profile(write(tmp_path, '[[sources]]\nid = "desk"\nkind = "feed"\nurl = "http://x"\n'))
    assert getattr(profile.sources[0], "url") == "http://x"


def test_durations():
    assert parse_duration("15m") == timedelta(minutes=15)
    assert parse_duration("36h") == timedelta(hours=36)
    assert parse_duration("2d") == timedelta(days=2)
    with pytest.raises(ValueError):
        parse_duration("soon")
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_profile.py -q`
Expected: `ModuleNotFoundError: No module named 'kestrel.profile'`.

- [ ] **Step 3: Implement**

`src/kestrel/profile.py`:

````python
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
    model_config = ConfigDict(extra="forbid")


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
    model_config = ConfigDict(extra="allow")

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
````


- [ ] **Step 4: Run them and watch them pass**

Run: `.venv/Scripts/python -m pytest tests/test_profile.py -q && .venv/Scripts/python -m pytest -q`
Expected: `11 passed`, then the whole suite green (the hygiene test includes the new example profile).

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/profile.py profile.example.toml tests/test_profile.py
git commit -m "feat(profile): profile.toml loader with plain-English errors and a demo default"
```

---

### Task 4: Connectors and the demo year

**Files:**
- Create: `src/kestrel/connectors/__init__.py`, `src/kestrel/connectors/base.py`, `src/kestrel/connectors/demo.py`
- Test: `tests/test_demo_connector.py`

**Interfaces:**
- Consumes: the contract (Task 1), `Profile` / `SourceCfg` (Task 3).
- Produces:
  - `Connector` protocol (`source_id`, `snapshot(now) -> Snapshot`) and `ConnectorUnavailable`.
  - `DemoConnector(source_id, tz, seed=340)`.
  - `weekdays_ending(end, count)`.
  - `build(cfg, profile) -> Connector`.
  - `collect(profile, now) -> Snapshot`: a failing source becomes a `Source(status="error")`, and a source older than its `stale_after` becomes `stale`.
- **Demo facts later tasks rely on** (seed 340, now = 2026-09-25T21:08Z):
  - 4 accounts, 5 books (`rsi2-real`, `rsi2-paper`, `ibs-paper`, `leader-paper`, `verticals-paper`), 4 strategies.
  - 34 real trades; `MSFT` held in `rsi2-real` with no stop.
  - A stale "Savings" source.
  - Six runs on weekdays and none on weekends.

- [ ] **Step 1: Write the failing tests**

`tests/test_demo_connector.py`:

````python
import datetime as dt
from zoneinfo import ZoneInfo

from kestrel.connectors import collect
from kestrel.connectors.demo import DemoConnector, weekdays_ending
from kestrel.profile import DEMO_PROFILE, Profile, SourceCfg

NY = ZoneInfo("America/New_York")
FRIDAY_EVENING = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)  # 17:08 in New York
SATURDAY = dt.datetime(2026, 9, 26, 15, 0, tzinfo=dt.timezone.utc)


def test_weekdays_ending_skips_weekends():
    days = weekdays_ending(dt.date(2026, 9, 27), 3)  # a Sunday
    assert days == [dt.date(2026, 9, 23), dt.date(2026, 9, 24), dt.date(2026, 9, 25)]


def test_the_demo_is_deterministic():
    a = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    b = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    assert a == b


def test_the_market_path_stays_put_as_the_dates_move():
    # monthly deposits follow the calendar, so account values shift a little; the market path does not
    today = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    a_week_on = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING + dt.timedelta(days=7))
    paper = lambda snap: next(b.value for b in snap.books if b.id == "rsi2-paper")  # noqa: E731
    assert paper(today) == paper(a_week_on)
    assert [t.return_pct for t in today.trades] == [t.return_pct for t in a_week_on.trades]
    assert a_week_on.account_history[0].points[-1].date == dt.date(2026, 10, 2)


def test_history_ends_today_and_accounts_match_their_last_point():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    history = {s.id: s.points for s in snap.account_history}
    for account in snap.accounts:
        assert history[account.id][-1].date == dt.date(2026, 9, 25)
        assert history[account.id][-1].value == account.value


def test_every_trade_and_position_belongs_to_a_book_and_every_book_to_a_strategy():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    books = {b.id for b in snap.books}
    strategies = {s.id for s in snap.strategies}
    assert {t.book_id for t in snap.trades} <= books
    assert {p.book_id for p in snap.positions} <= books
    assert {b.strategy_id for b in snap.books} <= strategies
    assert all(t.opened <= t.closed for t in snap.trades)


def test_runs_follow_the_clock_and_a_weekend_has_none():
    snap = DemoConnector("demo", NY).snapshot(FRIDAY_EVENING)
    status = {r.label: r.status for r in snap.runs}
    assert status["Morning run"] == "done" and status["Nightly suite"] == "due"
    assert DemoConnector("demo", NY).snapshot(SATURDAY).runs == []


def test_collect_marks_an_unknown_connector_as_an_error_and_keeps_going():
    profile = Profile(sources=[SourceCfg(id="demo", kind="demo"), SourceCfg(id="desk", kind="feed", label="Desk")])
    snap = collect(profile, FRIDAY_EVENING)
    desk = next(s for s in snap.sources if s.id == "desk")
    assert desk.status == "error" and "not available" in desk.detail
    assert len(snap.accounts) == 4  # the demo still arrived


def test_collect_marks_a_source_stale_after_its_threshold():
    profile = Profile(sources=[SourceCfg(id="demo", kind="demo", stale_after="1m")])
    snap = collect(profile, FRIDAY_EVENING)
    assert {s.label: s.status for s in snap.sources}["Portfolio"] == "stale"  # last success 2 minutes ago


def test_the_demo_profile_greets_alex():
    assert DEMO_PROFILE.you.name == "Alex"
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_demo_connector.py -q`
Expected: `ModuleNotFoundError: No module named 'kestrel.connectors'`.

- [ ] **Step 3: Implement**

`src/kestrel/connectors/base.py`:

````python
"""What every connector provides."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ..contract import Snapshot


class Connector(Protocol):
    source_id: str

    def snapshot(self, now: datetime) -> Snapshot:
        """Everything this source knows, as of `now`. Read-only: a connector never writes to its source."""
        ...


class ConnectorUnavailable(Exception):
    """The profile names a connector kind this version of kestrel does not have."""
````

`src/kestrel/connectors/__init__.py`:

````python
"""Connectors turn a profile's sources into one Snapshot."""

from __future__ import annotations

from datetime import datetime

from ..contract import Snapshot, Source, merge
from ..profile import Profile, SourceCfg
from .base import Connector, ConnectorUnavailable
from .demo import DemoConnector

__all__ = ["Connector", "ConnectorUnavailable", "build", "collect"]


def build(cfg: SourceCfg, profile: Profile) -> Connector:
    if cfg.kind == "demo":
        return DemoConnector(cfg.id, tz=profile.tz, seed=int(getattr(cfg, "seed", 340)))
    raise ConnectorUnavailable(f"connector kind {cfg.kind!r} is not available in this version of kestrel")


def _with_staleness(sources: list[Source], cfg: SourceCfg, now: datetime) -> list[Source]:
    out = []
    for s in sources:
        old = s.last_success is not None and now - s.last_success > cfg.stale_delta
        out.append(s.model_copy(update={"status": "stale"}) if s.status == "ok" and old else s)
    return out


def collect(profile: Profile, now: datetime) -> Snapshot:
    """Ask every source for its snapshot. One broken source shows as an error; it never takes the page down."""
    parts: list[Snapshot] = []
    failed: list[Source] = []
    for cfg in profile.sources:
        try:
            part = build(cfg, profile).snapshot(now)
        except Exception as exc:  # noqa: BLE001 - any connector failure becomes a visible source error
            failed.append(Source(id=cfg.id, label=cfg.label or cfg.id, kind=cfg.kind, status="error",
                                 detail=str(exc)[:200]))
            continue
        parts.append(part.model_copy(update={"sources": _with_staleness(list(part.sources), cfg, now)}))
    snapshot = merge(parts, generated_at=now)
    return snapshot.model_copy(update={"sources": [*snapshot.sources, *failed]})
````

`src/kestrel/connectors/demo.py`:

````python
"""Fictional demo data: a believable year for "Alex".

Deterministic for a seed: the numbers never change, only the dates move so the last point is today.
Nothing here is anyone's real account; the tickers are ordinary large caps and sector funds.
"""

from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..contract import (
    Account,
    Benchmark,
    Book,
    Expected,
    Position,
    Run,
    Series,
    Snapshot,
    Source,
    Step,
    Strategy,
    Trade,
    ValuePoint,
)

DAYS = 262  # about a year of weekdays
MARKET_DRIFT, MARKET_VOL = 0.00022, 0.0085  # a daily market factor every account leans on
STOCKS = ["HD", "LOW", "MRK", "PEP", "WMT", "TXN", "MCD", "KO", "ABT", "UNP", "ORCL", "COST", "UNH", "CSCO", "HON"]
FUNDS = ["XLE", "XLK", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "SPY"]
# backtest share of trades (%) per 1-point bucket from -10% to +10%; sums to 100
RSI2_DISTRIBUTION = [
    0.2, 3.1, 1.2, 0.3, 0.6, 1.1, 2.0, 4.9, 9.2, 10.9, 11.8, 14.6, 17.3, 12.1, 6.4, 2.6, 1.0, 0.4, 0.2, 0.1,
]


def weekdays_ending(end: date, count: int) -> list[date]:
    """The `count` weekdays up to and including `end` (or the Friday before, on a weekend), oldest first."""
    days: list[date] = []
    day = end
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return days[::-1]


def _next_weekday_at(now: datetime, at: time) -> datetime:
    candidate = datetime.combine(now.date(), at, tzinfo=now.tzinfo)
    while candidate <= now or candidate.weekday() >= 5:
        candidate = datetime.combine(candidate.date() + timedelta(days=1), at, tzinfo=now.tzinfo)
    return candidate


def _monthly(days: list[date], amount: float) -> list[float]:
    return [amount if i > 0 and days[i].month != days[i - 1].month else 0.0 for i in range(len(days))]


def _walk(rng: random.Random, start: float, market: list[float], beta: float, drift: float, vol: float,
          flows: list[float]) -> list[float]:
    values = [start]
    for i in range(1, len(market)):
        step = drift + beta * market[i] + rng.gauss(0.0, vol)
        values.append(round(values[-1] * (1.0 + step) + flows[i], 2))
    return values


def _points(days: list[date], values: list[float], flows: list[float]) -> list[ValuePoint]:
    return [ValuePoint(date=d, value=v, net_flow=f) for d, v, f in zip(days, values, flows)]


def _trades(rng: random.Random, book_id: str, days: list[date], count: int, *, win_p: float, win_mu: float,
            loss_mu: float, stop_every: int = 0, stop_pct: float | None = None, hold: tuple[int, int] = (1, 6),
            lot: float = 3000.0, pool: list[str] = STOCKS) -> list[Trade]:
    trades: list[Trade] = []
    span = max(1, len(days) - 8)
    for k in range(count):
        opened_i = min(len(days) - 2, 2 + (k * span) // count + rng.randint(0, 2))
        closed_i = min(opened_i + rng.randint(*hold), len(days) - 2)
        if stop_every and k % stop_every == stop_every - 1:
            ret, reason = -(stop_pct or 8.0) - rng.random() * 0.4, "stop"
        elif rng.random() < win_p:
            ret, reason = win_mu * (0.3 + rng.random() * 1.4), "signal"
        else:
            ret, reason = loss_mu * (0.3 + rng.random() * 1.4), "signal"
        entry = round(40 + rng.random() * 460, 2)
        quantity = max(1, int(lot // entry))
        exit_price = round(entry * (1 + ret / 100), 2)
        trades.append(Trade(
            book_id=book_id, symbol=pool[rng.randrange(len(pool))], opened=days[opened_i], closed=days[closed_i],
            entry_price=entry, exit_price=exit_price, quantity=quantity, pnl=round((exit_price - entry) * quantity, 2),
            return_pct=round(ret, 2), r_multiple=round(ret / stop_pct, 2) if stop_pct else None, exit_reason=reason,
        ))
    return trades


STRATEGIES = [
    Strategy(
        id="rsi2", name="Mean reversion", summary="Buys large, liquid stocks after a sharp short-term drop inside an "
        "uptrend, and sells into the bounce — usually within a week.",
        steps=[
            Step(label="Universe", title="Large US stocks", text="Only while the stock sits above its 200-day average",
                 params=["200-day filter"]),
            Step(label="Entry", title="Buy after a sharp drop", text="RSI(2) closes under 10 → buy at the next open",
                 params=["RSI(2) < 10", "next open"]),
            Step(label="Protect", title="A stop rests at the broker", text="8% under the buy price — never lowered",
                 params=["−8% stop", "GTC"]),
            Step(label="Exit", title="Sell into the bounce",
                 text="RSI(2) closes over 70 → sell at the next open, or the stop fills",
                 params=["RSI(2) > 70", "or stop"]),
        ],
        sizing="Each position is the account value ÷ 6, at most 5 open.",
        expected=Expected(win_rate=66, avg_trade_pct=0.84, avg_win_pct=2.45, avg_loss_pct=-2.28, trades_per_month=3.1,
                          sd_trade_pct=3.0, distribution=RSI2_DISTRIBUTION, source="backtest", window="2006–2020"),
        review_at_trades=50,
    ),
    Strategy(
        id="ibs", name="ETF close strength",
        summary="Buys a sector fund that closes near the bottom of its day's range and holds until it closes near "
        "the top.",
        expected=Expected(win_rate=62, avg_trade_pct=0.35, avg_win_pct=1.3, avg_loss_pct=-1.2, trades_per_month=6.0,
                          sd_trade_pct=1.6, source="backtest", window="2000–2020"),
        review_at_trades=30,
    ),
    Strategy(
        id="leader", name="Opening leader", summary="Buys the strongest name of the first fifteen minutes and is flat "
        "before lunch.",
        expected=Expected(win_rate=52, avg_trade_pct=0.10, avg_win_pct=1.0, avg_loss_pct=-0.9, trades_per_month=15.0,
                          sd_trade_pct=1.2, source="backtest", window="2021–2024"),
        review_at_trades=30,
    ),
    Strategy(
        id="verticals", name="Options verticals", summary="Expresses swing signals as debit spreads.",
        expected=Expected(win_rate=55, avg_trade_pct=4.0, avg_win_pct=38.0, avg_loss_pct=-40.0, trades_per_month=4.0,
                          sd_trade_pct=35.0, source="backtest", window="2015–2020"),
        review_at_trades=30,
    ),
]


class DemoConnector:
    """Serves the same fictional year to anyone who runs kestrel without a profile."""

    def __init__(self, source_id: str, tz: ZoneInfo, seed: int = 340) -> None:
        self.source_id = source_id
        self.tz = tz
        self.seed = seed

    def snapshot(self, now: datetime) -> Snapshot:
        local = now.astimezone(self.tz)
        days = weekdays_ending(local.date(), DAYS)
        rng = random.Random(self.seed)
        market = [0.0] + [rng.gauss(MARKET_DRIFT, MARKET_VOL) for _ in range(DAYS - 1)]
        zero = [0.0] * DAYS

        roth_flows, brokerage_flows, savings_flows = _monthly(days, 500), _monthly(days, 550), _monthly(days, 150)
        trading_flows = zero.copy()
        trading_flows[DAYS // 3] = 1500.0
        roth = _walk(rng, 50200.0, market, 0.95, 0.0001, 0.0015, roth_flows)
        brokerage = _walk(rng, 37400.0, market, 1.0, 0.0001, 0.0018, brokerage_flows)
        trading = _walk(rng, 14200.0, market, 0.45, 0.0006, 0.0045, trading_flows)
        savings = [21500.0]
        for i in range(1, DAYS):
            savings.append(round(savings[-1] * (1 + 0.041 / 260) + savings_flows[i], 2))
        spx = _walk(rng, 560.0, market, 1.0, 0.0, 0.0015, zero)
        paper = _walk(rng, 100000.0, market, 0.5, 0.0005, 0.004, zero)
        options = _walk(rng, 100000.0, market, 0.8, -0.0002, 0.012, zero)
        paused_at = DAYS - 20
        options = options[:paused_at] + [options[paused_at - 1]] * (DAYS - paused_at)
        ibs_days, leader_days = days[-12:], days[-10:]
        ibs = _walk(rng, 3200.0, market[-12:], 0.4, 0.0012, 0.004, zero[:12])
        leader = _walk(rng, 25000.0, market[-10:], 0.2, -0.0015, 0.003, zero[:10])

        as_of = datetime.combine(days[-1], time(16, 0), tzinfo=self.tz)
        accounts = [
            Account(id="roth", name="Roth IRA", institution="Brokerage A", category="long_term", value=roth[-1],
                    as_of=as_of),
            Account(id="brokerage", name="Brokerage", institution="Brokerage A", category="long_term",
                    value=brokerage[-1], as_of=as_of),
            Account(id="trading", name="Trading account", institution="Brokerage B", category="trading",
                    value=trading[-1], as_of=as_of),
            Account(id="savings", name="High-yield savings", institution="Bank C", category="cash", value=savings[-1],
                    as_of=as_of),
        ]
        account_history = [
            Series(id="roth", points=_points(days, roth, roth_flows)),
            Series(id="brokerage", points=_points(days, brokerage, brokerage_flows)),
            Series(id="trading", points=_points(days, trading, trading_flows)),
            Series(id="savings", points=_points(days, savings, savings_flows)),
        ]

        at = lambda hh, mm: _next_weekday_at(local, time(hh, mm))  # noqa: E731
        books = [
            Book(id="rsi2-real", name="Mean reversion", money="real", strategy_id="rsi2", account_id="trading",
                 status="running", started=days[0] - timedelta(days=5), value=trading[-1], slots_total=5,
                 next_run=at(9, 31)),
            Book(id="rsi2-paper", name="Mean reversion", money="paper", strategy_id="rsi2", status="running",
                 started=days[0] - timedelta(days=60), value=paper[-1], slots_total=6, next_run=at(17, 30)),
            Book(id="ibs-paper", name="ETF close strength", money="paper", strategy_id="ibs", status="running",
                 started=ibs_days[0], value=ibs[-1], slots_total=4, next_run=at(15, 56)),
            Book(id="leader-paper", name="Opening leader", money="paper", strategy_id="leader", status="running",
                 started=leader_days[0], value=leader[-1], slots_total=1, next_run=at(9, 25)),
            Book(id="verticals-paper", name="Options verticals", money="paper", strategy_id="verticals",
                 status="paused", started=days[0] - timedelta(days=70), value=options[-1], slots_total=3),
        ]
        book_history = [
            Series(id="rsi2-real", points=_points(days, trading, trading_flows)),
            Series(id="rsi2-paper", points=_points(days, paper, zero)),
            Series(id="ibs-paper", points=_points(ibs_days, ibs, zero[:12])),
            Series(id="leader-paper", points=_points(leader_days, leader, zero[:10])),
            Series(id="verticals-paper", points=_points(days, options, zero)),
        ]
        trades = (
            _trades(rng, "rsi2-real", days, 34, win_p=0.72, win_mu=2.4, loss_mu=-1.4, stop_every=17, stop_pct=8.0)
            + _trades(rng, "rsi2-paper", days, 71, win_p=0.72, win_mu=2.4, loss_mu=-1.4, stop_every=17, stop_pct=8.0,
                      lot=18000.0)
            + _trades(rng, "ibs-paper", ibs_days, 7, win_p=0.6, win_mu=1.2, loss_mu=-0.9, lot=800.0, pool=FUNDS)
            + _trades(rng, "leader-paper", leader_days, 11, win_p=0.3, win_mu=1.0, loss_mu=-1.6, hold=(0, 0),
                      lot=24000.0)
            + _trades(rng, "verticals-paper", days[:paused_at], 13, win_p=0.35, win_mu=30.0, loss_mu=-35.0, lot=600.0)
        )
        positions = [
            Position(book_id="rsi2-real", symbol="MSFT", quantity=6, entry_price=508.20, last_price=512.40,
                     opened=days[-1]),
            Position(book_id="rsi2-real", symbol="CAT", quantity=6, entry_price=468.30, last_price=474.95,
                     stop_price=430.84, opened=days[-3]),
            Position(book_id="rsi2-real", symbol="PG", quantity=20, entry_price=152.40, last_price=155.08,
                     stop_price=140.21, opened=days[-4]),
            Position(book_id="rsi2-real", symbol="JPM", quantity=10, entry_price=301.10, last_price=297.85,
                     stop_price=277.01, opened=days[-2]),
            Position(book_id="rsi2-paper", symbol="HD", quantity=45, entry_price=398.10, last_price=404.66,
                     stop_price=366.25, opened=days[-3]),
            Position(book_id="rsi2-paper", symbol="TXN", quantity=95, entry_price=190.20, last_price=188.70,
                     stop_price=174.98, opened=days[-2]),
            Position(book_id="rsi2-paper", symbol="KO", quantity=260, entry_price=69.05, last_price=69.90,
                     stop_price=63.53, opened=days[-5]),
            Position(book_id="rsi2-paper", symbol="ABT", quantity=140, entry_price=128.40, last_price=130.02,
                     stop_price=118.13, opened=days[-4]),
            Position(book_id="rsi2-paper", symbol="UNP", quantity=75, entry_price=238.55, last_price=241.10,
                     stop_price=219.47, opened=days[-1]),
            Position(book_id="ibs-paper", symbol="XLF", quantity=17, entry_price=51.20, last_price=51.62,
                     opened=days[-1], note="Exits on strength"),
        ]
        sid = self.source_id
        sources = [
            Source(id=f"{sid}-portfolio", label="Portfolio", kind="data collector",
                   last_success=now - timedelta(minutes=2)),
            Source(id=f"{sid}-desk", label="Trading desk", kind="feed", last_success=now - timedelta(minutes=1)),
            Source(id=f"{sid}-paper", label="Paper broker", kind="rails", last_success=now - timedelta(minutes=6)),
            Source(id=f"{sid}-savings", label="Savings", kind="bank link", last_success=now - timedelta(hours=26),
                   status="stale"),
        ]
        return Snapshot(
            generated_at=now, sources=sources, accounts=accounts, account_history=account_history, books=books,
            book_history=book_history, positions=positions, trades=trades, strategies=STRATEGIES,
            runs=self._runs(local), benchmark=Benchmark(symbol="SPY", label="S&P 500", points=_points(days, spx, zero)),
        )

    def _runs(self, local: datetime) -> list[Run]:
        if local.weekday() >= 5:
            return []
        plan = [
            (time(9, 25), "Opening leader · paper", "leader-paper", "Screens at 09:45", "Screened at 09:45 · no entry"),
            (time(9, 31), "Morning run", "rsi2-real", "Places queued entries and exits",
             "1 exit sold · MSFT entry filled"),
            (time(15, 56), "ETF close entries · paper", "ibs-paper", "Buys funds that close weak",
             "Bought XLF at the close"),
            (time(17, 30), "Nightly suite", None, "Signals, paper fills, the nightly note", "Nightly note written"),
            (time(17, 45), "Evening run", "rsi2-real", "Queues the next session's entries and exits",
             "Queued 1 entry"),
            (time(19, 0), "Watchdog", None, "Checks every run reported in", "All runs reported in"),
        ]
        runs = []
        for at, label, book_id, due_detail, done_detail in plan:
            when = datetime.combine(local.date(), at, tzinfo=local.tzinfo)
            done = when <= local
            runs.append(Run(time=when, label=label, book_id=book_id, status="done" if done else "due",
                            detail=done_detail if done else due_detail))
        return runs
````


- [ ] **Step 4: Run them and watch them pass**

Run: `.venv/Scripts/python -m pytest tests/test_demo_connector.py -q && .venv/Scripts/python -m ruff check .`
Expected: `9 passed`; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/connectors tests/test_demo_connector.py
git commit -m "feat(connectors): collect() and a deterministic, fictional demo year"
```

---

### Task 5: The Home and shell views

**Files:**
- Create: `src/kestrel/views/__init__.py`, `src/kestrel/views/home.py`, `src/kestrel/views/shell.py`
- Test: `tests/test_home_view.py`

**Interfaces:**
- Consumes: `collect`, the contract, the metrics and `Profile`.
- Produces:
  - `home_view(snapshot, profile, now) -> HomeView`. Its fields are `as_of`, `summary`, `net_worth`, `allocation`, `accounts`, `comparison`, `attention`, `books`, `today` and `positions`; the exact names are in the code, and `web/src/lib/api.ts` (Task 9) mirrors them.
  - `shell_view(snapshot, profile, now) -> ShellView` (`name`, `app`, `benchmark_label`, `now`, `sources`, `counts`).
  - `age_text(timedelta) -> str` ("26 hours").
  - Verdict thresholds: fewer than 10 closed trades is `early`; otherwise the per-trade average is compared with `expected_band`.

- [ ] **Step 1: Write the failing tests**

`tests/test_home_view.py`:

````python
import datetime as dt

import pytest

from kestrel.connectors import collect
from kestrel.contract import Account, Book, Position, Series, Snapshot, Source, Strategy, Trade, ValuePoint
from kestrel.profile import DEMO_PROFILE, Profile
from kestrel.views.home import home_view

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def demo_home():
    return home_view(collect(DEMO_PROFILE, NOW), DEMO_PROFILE, NOW)


def test_net_worth_is_the_sum_of_accounts(demo_home):
    assert demo_home.net_worth.total == pytest.approx(sum(a.value for a in demo_home.accounts))
    assert demo_home.net_worth.points[-1].value == pytest.approx(demo_home.net_worth.total)


def test_allocation_fills_exactly_one_hundred_cells(demo_home):
    assert sum(s.cells for s in demo_home.allocation) == 100
    assert [s.category for s in demo_home.allocation] == ["long_term", "trading", "cash"]


def test_the_comparison_is_year_to_date_with_three_aligned_lines(demo_home):
    c = demo_home.comparison
    assert c.window == "ytd" and c.dates[0] >= dt.date(2026, 1, 1)
    assert [line.key for line in c.lines] == ["trading", "long_term", "benchmark"]
    assert all(len(line.values) == len(c.dates) for line in c.lines)
    assert c.lines[0].values[0] == 0.0
    assert c.gap_pts == pytest.approx(c.lines[0].return_pct - c.lines[1].return_pct, abs=0.01)
    assert c.real_trades == 34 and c.review_at == 50


def test_attention_is_ordered_serious_warning_note(demo_home):
    levels = [a.level for a in demo_home.attention]
    assert levels == sorted(levels, key=["serious", "warning", "note"].index)
    titles = [a.title for a in demo_home.attention]
    assert "MSFT has no resting stop" in titles
    assert any("Savings" in t for t in titles)
    assert demo_home.summary.needs_you == 2


def test_book_verdicts(demo_home):
    verdicts = {b.id: b.verdict for b in demo_home.books}
    assert verdicts["rsi2-real"] == "in_band"
    assert verdicts["ibs-paper"] == "early"  # 7 trades is too few to judge
    assert verdicts["leader-paper"] == "below"


def test_positions_list_real_money_first_and_an_unprotected_one_first_of_all(demo_home):
    first = demo_home.positions[0]
    assert (first.symbol, first.money, first.room_pct) == ("MSFT", "real", None)
    assert all(p.money == "real" for p in demo_home.positions[:4])


def test_today_holds_only_today(demo_home):
    assert [r.label for r in demo_home.today][:2] == ["Opening leader · paper", "Morning run"]


def _tiny(accounts, history, books=(), book_history=(), trades=(), positions=(), strategies=(), sources=()):
    return Snapshot(generated_at=NOW, accounts=list(accounts), account_history=list(history), books=list(books),
                    book_history=list(book_history), trades=list(trades), positions=list(positions),
                    strategies=list(strategies), sources=list(sources))


def test_an_empty_snapshot_still_renders():
    home = home_view(_tiny([], []), Profile(), NOW)
    assert home.net_worth.total == 0 and home.allocation == [] and home.comparison.lines == []
    assert home.comparison.gap_pts is None and home.books == [] and home.attention == []


def test_early_january_falls_back_to_twelve_months():
    days = [dt.date(2025, 12, 30) - dt.timedelta(days=i) for i in range(30)][::-1] + [dt.date(2026, 1, 2)]
    points = [ValuePoint(date=d, value=100 + i) for i, d in enumerate(days)]
    acct = Account(id="a", name="A", category="long_term", value=points[-1].value, as_of=NOW)
    home = home_view(_tiny([acct], [Series(id="a", points=points)]), Profile(), NOW.replace(month=1, day=2))
    assert home.comparison.window == "12m"
    assert len(home.comparison.dates) == len(days)


def test_a_paper_position_without_a_stop_is_not_an_alarm():
    book = Book(id="p", name="Paper", money="paper", strategy_id="s", status="running", started=dt.date(2026, 1, 1),
                value=1000)
    pos = Position(book_id="p", symbol="XLF", quantity=1, entry_price=50, last_price=51, opened=dt.date(2026, 9, 25))
    home = home_view(_tiny([], [], books=[book], positions=[pos]), Profile(), NOW)
    assert home.attention == []


def test_an_error_source_becomes_a_warning():
    src = Source(id="desk", label="Trading desk", kind="feed", status="error", detail="timed out")
    home = home_view(_tiny([], [], sources=[src]), Profile(), NOW)
    assert [(a.level, a.title) for a in home.attention] == [("warning", "Trading desk couldn’t be read")]


def test_a_book_without_history_or_trades_has_no_numbers_but_still_shows():
    book = Book(id="b", name="New", money="real", strategy_id="s", status="running", started=dt.date(2026, 9, 25),
                value=500, slots_total=3)
    strat = Strategy(id="s", name="New strategy")
    trade = Trade(book_id="b", symbol="HD", opened=dt.date(2026, 9, 24), closed=dt.date(2026, 9, 25),
                  entry_price=10, exit_price=11, quantity=1, pnl=1, return_pct=10)
    home = home_view(_tiny([], [], books=[book], strategies=[strat], trades=[trade]), Profile(), NOW)
    row = home.books[0]
    assert row.day_change is None and row.since_pct is None
    assert row.verdict == "none"  # no expectation to compare with
    assert row.slots_used == 0 and row.slots_total == 3
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_home_view.py -q`
Expected: `ModuleNotFoundError: No module named 'kestrel.views'`.

- [ ] **Step 3: Implement**

`src/kestrel/views/__init__.py`:

````python
"""Page view models: what each page needs, computed from one Snapshot."""
````

`src/kestrel/views/home.py`:

````python
"""The Home page, computed from one Snapshot: how is all my money doing, and does anything need me?"""

from __future__ import annotations

import datetime as dt
from statistics import fmean
from typing import Literal

from pydantic import BaseModel

from ..contract import Book, Snapshot, Source, ValuePoint
from ..metrics import expected_band, growth_index, largest_remainder, max_drawdown_pct, sum_series
from ..profile import Profile

CATEGORY_LABELS = {"long_term": "Long-term", "trading": "Trading", "cash": "Cash", "other": "Other"}
MIN_TRADES_FOR_VERDICT = 10  # fewer closed trades than this is "too early" to judge a book
MIN_YTD_POINTS = 5  # early January falls back to the past twelve months


class View(BaseModel):
    pass


class Delta(View):
    amount: float
    pct: float | None


class NetWorth(View):
    total: float
    today: Delta
    month: Delta
    year: Delta
    year_flows: float
    points: list[ValuePoint]  # the client draws the "starting value + deposits" line from net_flow


class Slice(View):
    category: str
    label: str
    value: float
    share: float
    cells: int  # of 100, for the waffle


class AccountRow(View):
    id: str
    name: str
    category: str
    value: float
    day_pct: float | None


class Line(View):
    key: Literal["trading", "long_term", "benchmark"]
    label: str
    return_pct: float
    max_drop_pct: float
    values: list[float | None]  # percent change since the window start, aligned with Comparison.dates


class Comparison(View):
    window: Literal["ytd", "12m"]
    dates: list[dt.date]
    lines: list[Line]
    gap_pts: float | None  # trading minus long-term, in percentage points
    shallower: bool | None  # trading's worst drop was smaller than long-term's
    real_trades: int
    review_at: int | None


class Attention(View):
    level: Literal["serious", "warning", "note"]
    title: str
    detail: str
    link: str


class BookRow(View):
    id: str
    name: str
    strategy: str
    money: Literal["real", "paper"]
    status: str
    value: float
    day_change: float | None
    since_pct: float | None
    started: dt.date
    trades: int
    per_trade_pct: float | None
    band_lo: float | None
    band_hi: float | None
    verdict: Literal["in_band", "below", "above", "early", "none"]
    slots_used: int
    slots_total: int | None
    next_run: dt.datetime | None


class TodayRun(View):
    time: dt.datetime
    label: str
    status: str
    detail: str


class PositionRow(View):
    book_id: str
    book: str
    symbol: str
    money: Literal["real", "paper"]
    quantity: float
    entry_price: float
    last_price: float
    stop_price: float | None
    room_pct: float | None  # distance from the last price down to the stop
    pnl: float
    note: str


class Summary(View):
    day_change: float
    gap_pts: float | None
    needs_you: int  # serious + warning items


class HomeView(View):
    as_of: dt.datetime
    summary: Summary
    net_worth: NetWorth
    allocation: list[Slice]
    accounts: list[AccountRow]
    comparison: Comparison
    attention: list[Attention]
    books: list[BookRow]
    today: list[TodayRun]
    positions: list[PositionRow]


def _delta(points: list[ValuePoint], since: dt.date) -> Delta:
    """Money change from the last point before `since` to the latest point (deposits included)."""
    if not points:
        return Delta(amount=0.0, pct=None)
    base = next((p.value for p in reversed(points) if p.date < since), points[0].value)
    amount = points[-1].value - base
    return Delta(amount=round(amount, 2), pct=round(amount / base * 100, 2) if base else None)


def _day_pct(points: list[ValuePoint]) -> float | None:
    if len(points) < 2 or points[-2].value <= 0:
        return None
    return round(((points[-1].value - points[-1].net_flow) / points[-2].value - 1) * 100, 2)


def age_text(delta: dt.timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    hours = minutes // 60
    if hours < 48:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    return f"{hours // 24} days"


def _window(points: list[ValuePoint], start: dt.date) -> list[ValuePoint]:
    return [p for p in points if p.date >= start]


def _line(key, label, points: list[ValuePoint], dates: list[dt.date]) -> Line | None:
    if len(points) < 2:
        return None
    index = growth_index(points)
    by_date = {p.date: i for p, i in zip(points, index)}
    values: list[float | None] = []
    last: float | None = None
    for day in dates:
        last = by_date.get(day, last)
        values.append(None if last is None else round((last - 1) * 100, 3))
    return Line(key=key, label=label, return_pct=round((index[-1] - 1) * 100, 2),
                max_drop_pct=round(max_drawdown_pct(index), 2), values=values)


def _comparison(snapshot: Snapshot, profile: Profile, today: dt.date, real_books: list[Book]) -> Comparison:
    history = {s.id: s.points for s in snapshot.account_history}
    book_history = {s.id: s.points for s in snapshot.book_history}
    trading = sum_series([book_history[b.id] for b in real_books if b.id in book_history])
    long_term = sum_series([history[a.id] for a in snapshot.accounts if a.category == "long_term" and a.id in history])
    bench = list(snapshot.benchmark.points) if snapshot.benchmark else []
    start, window = dt.date(today.year, 1, 1), "ytd"
    if len(_window(trading or long_term, start)) < MIN_YTD_POINTS:
        start, window = today - dt.timedelta(days=365), "12m"
    trading, long_term, bench = _window(trading, start), _window(long_term, start), _window(bench, start)
    dates = sorted({p.date for p in (trading or long_term or bench)})
    lines = [
        line for line in (
            _line("trading", "Trading", trading, dates),
            _line("long_term", "Long-term", long_term, dates),
            _line("benchmark", snapshot.benchmark.label if snapshot.benchmark else profile.benchmark.label, bench,
                  dates),
        ) if line is not None
    ]
    by_key = {line.key: line for line in lines}
    t, lt = by_key.get("trading"), by_key.get("long_term")
    real_ids = {b.id for b in real_books}
    review = [s.review_at_trades for s in snapshot.strategies
              if s.review_at_trades and s.id in {b.strategy_id for b in real_books}]
    return Comparison(
        window=window, dates=dates, lines=lines,
        gap_pts=round(t.return_pct - lt.return_pct, 2) if t and lt else None,
        shallower=(t.max_drop_pct > lt.max_drop_pct) if t and lt else None,
        real_trades=sum(1 for tr in snapshot.trades if tr.book_id in real_ids),
        review_at=min(review) if review else None,
    )


def _book_rows(snapshot: Snapshot) -> list[BookRow]:
    history = {s.id: s.points for s in snapshot.book_history}
    strategies = {s.id: s for s in snapshot.strategies}
    rows = []
    for book in snapshot.books:
        points = list(history.get(book.id, []))
        returns = [t.return_pct for t in snapshot.trades if t.book_id == book.id]
        strategy = strategies.get(book.strategy_id)
        expected = strategy.expected if strategy else None
        per_trade = round(fmean(returns), 3) if returns else None
        lo = hi = None
        if not returns or expected is None:
            verdict = "none"
        elif len(returns) < MIN_TRADES_FOR_VERDICT:
            verdict = "early"
        else:
            lo, hi = expected_band(expected.avg_trade_pct, expected.sd_trade_pct, len(returns))
            verdict = "below" if per_trade < lo else "above" if per_trade > hi else "in_band"
        rows.append(BookRow(
            id=book.id, name=book.name, strategy=strategy.name if strategy else book.strategy_id, money=book.money,
            status=book.status, value=book.value,
            day_change=round(points[-1].value - points[-2].value - points[-1].net_flow, 2) if len(points) > 1 else None,
            since_pct=round((growth_index(points)[-1] - 1) * 100, 2) if len(points) > 1 else None,
            started=book.started, trades=len(returns), per_trade_pct=per_trade,
            band_lo=round(lo, 3) if lo is not None else None, band_hi=round(hi, 3) if hi is not None else None,
            verdict=verdict, slots_used=sum(1 for p in snapshot.positions if p.book_id == book.id),
            slots_total=book.slots_total, next_run=book.next_run,
        ))
    return rows


def _source_attention(source: Source, now: dt.datetime, tz: dt.tzinfo) -> Attention | None:
    if source.status == "error":
        return Attention(level="warning", title=f"{source.label} couldn’t be read", detail=source.detail,
                         link="/settings")
    if source.status == "stale" and source.last_success is not None:
        when = source.last_success.astimezone(tz).strftime("%a %H:%M")
        age = age_text(now - source.last_success)
        return Attention(level="warning", title=f"{source.label} hasn’t synced in {age}",
                         detail=f"{source.kind} · last success {when}", link="/settings")
    return None


def _attention(snapshot: Snapshot, rows: list[BookRow], strategies_review: dict[str, int | None],
               now: dt.datetime, tz: dt.tzinfo) -> list[Attention]:
    books = {b.id: b for b in snapshot.books}
    items: list[Attention] = []
    for p in snapshot.positions:
        book = books.get(p.book_id)
        if book is not None and book.money == "real" and p.stop_price is None:
            items.append(Attention(level="serious", title=f"{p.symbol} has no resting stop",
                                   detail=f"{book.name} · real — no protective stop on record", link="/books"))
    for source in snapshot.sources:
        item = _source_attention(source, now, tz)
        if item:
            items.append(item)
    for row in rows:
        if row.verdict == "below":
            review = strategies_review.get(row.id)
            detail = f"{row.trades} of {review} {row.money} trades · reviewed at {review}" if review else \
                f"{row.trades} {row.money} trades"
            items.append(Attention(level="note", title=f"{row.name} is below its expected band", detail=detail,
                                   link="/strategies"))
    items.extend(Attention(level=a.level, title=a.title, detail=a.detail, link=a.link) for a in snapshot.alerts)
    order = {"serious": 0, "warning": 1, "note": 2}
    return sorted(items, key=lambda a: order[a.level])


def home_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> HomeView:
    tz = profile.tz
    today = now.astimezone(tz).date()
    history = {s.id: s.points for s in snapshot.account_history}
    net = sum_series([history[a.id] for a in snapshot.accounts if a.id in history])
    total = round(sum(a.value for a in snapshot.accounts), 2)
    net_worth = NetWorth(
        total=total,
        today=_delta(net, today), month=_delta(net, today.replace(day=1)), year=_delta(net, dt.date(today.year, 1, 1)),
        year_flows=round(sum(p.net_flow for p in net[1:] if p.date >= dt.date(today.year, 1, 1)), 2),
        points=net,
    )
    order = ["long_term", "trading", "cash", "other"]
    values = {c: sum(a.value for a in snapshot.accounts if a.category == c) for c in order}
    present = [c for c in order if values[c] > 0]
    cells = largest_remainder([values[c] for c in present])
    allocation = [
        Slice(category=c, label=CATEGORY_LABELS[c], value=round(values[c], 2),
              share=round(values[c] / total * 100, 2) if total else 0.0, cells=n)
        for c, n in zip(present, cells)
    ]
    accounts = [AccountRow(id=a.id, name=a.name, category=a.category, value=a.value,
                           day_pct=_day_pct(list(history.get(a.id, [])))) for a in snapshot.accounts]
    real_books = [b for b in snapshot.books if b.money == "real"]
    comparison = _comparison(snapshot, profile, today, real_books)
    rows = _book_rows(snapshot)
    review_by_book = {b.id: next((s.review_at_trades for s in snapshot.strategies if s.id == b.strategy_id), None)
                      for b in snapshot.books}
    attention = _attention(snapshot, rows, review_by_book, now, tz)
    books = {b.id: b for b in snapshot.books}
    positions = [
        PositionRow(
            book_id=p.book_id, book=books[p.book_id].name if p.book_id in books else p.book_id, symbol=p.symbol,
            money=books[p.book_id].money if p.book_id in books else "paper", quantity=p.quantity,
            entry_price=p.entry_price, last_price=p.last_price, stop_price=p.stop_price,
            room_pct=round((p.last_price - p.stop_price) / p.last_price * 100, 2)
            if p.stop_price is not None and p.last_price > 0 else None,
            pnl=round((p.last_price - p.entry_price) * p.quantity, 2), note=p.note,
        )
        for p in snapshot.positions
    ]
    positions.sort(key=lambda r: (r.money != "real", r.room_pct is not None, r.symbol))
    runs = sorted((r for r in snapshot.runs if r.time.astimezone(tz).date() == today), key=lambda r: r.time)
    return HomeView(
        as_of=now,
        summary=Summary(day_change=net_worth.today.amount, gap_pts=comparison.gap_pts,
                        needs_you=sum(1 for a in attention if a.level in ("serious", "warning"))),
        net_worth=net_worth, allocation=allocation, accounts=accounts, comparison=comparison, attention=attention,
        books=rows, today=[TodayRun(time=r.time, label=r.label, status=r.status, detail=r.detail) for r in runs],
        positions=positions,
    )
````

`src/kestrel/views/shell.py`:

````python
"""What the app shell needs on every page: who you are, how it looks, and how fresh each source is."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel

from ..contract import Snapshot, Source
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


def shell_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> ShellView:
    return ShellView(
        name=profile.you.name,
        app=profile.app,
        benchmark_label=profile.benchmark.label,
        now=now,
        sources=list(snapshot.sources),
        counts=NavCounts(accounts=len(snapshot.accounts), books=len(snapshot.books),
                         strategies=len(snapshot.strategies)),
    )
````


- [ ] **Step 4: Run them and watch them pass**

Run: `.venv/Scripts/python -m pytest tests/test_home_view.py -q && .venv/Scripts/python -m ruff check .`
Expected: `12 passed`; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/views tests/test_home_view.py
git commit -m "feat(views): Home and shell view models computed from one Snapshot"
```

---

### Task 6: The read-only server

**Files:**
- Create: `src/kestrel/server.py`
- Test: `tests/test_server.py`, `tests/test_read_only_guard.py`

**Interfaces:**
- Consumes: `collect`, `home_view`, `shell_view`.
- Produces: `create_app(profile, *, clock=utcnow, web_dist=WEB_DIST) -> FastAPI` with:
  - `GET /api/health`, `/api/shell`, `/api/home`;
  - a JSON 404 for other `/api/*` paths;
  - `/assets/*` and the SPA fallback to `index.html` when `web_dist` holds a build.
  
  `WEB_DIST` = `<repo>/web/dist`.

- [ ] **Step 1: Write the failing tests**

`tests/test_server.py`:

````python
import datetime as dt

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from kestrel.profile import DEMO_PROFILE
from kestrel.server import create_app

NOW = dt.datetime(2026, 9, 25, 21, 8, tzinfo=dt.timezone.utc)


@pytest.fixture
def dist(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>kestrel</title>", encoding="utf-8")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(dist):
    return TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist))


def test_every_route_is_read_only(dist):
    app = create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=dist)
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    assert routes, "expected API routes"
    for route in routes:
        assert route.methods <= {"GET", "HEAD"}, f"{route.path} allows {route.methods}"


def test_writes_are_refused(client):
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/home").status_code == 405


def test_health_shell_and_home(client):
    assert client.get("/api/health").json()["ok"] is True
    shell = client.get("/api/shell").json()
    assert shell["name"] == "Alex" and shell["app"]["accent"] == "rufous"
    assert shell["counts"] == {"accounts": 4, "books": 5, "strategies": 4}
    home = client.get("/api/home").json()
    assert home["summary"]["needs_you"] == 2
    assert home["net_worth"]["total"] > 0


def test_the_shell_never_exposes_source_settings(client, tmp_path):
    body = client.get("/api/shell").text
    assert "stale_after" not in body and "token_env" not in body


def test_an_unknown_api_path_is_a_json_404(client):
    response = client.get("/api/nope")
    assert response.status_code == 404 and "no such endpoint" in response.json()["detail"]


def test_pages_fall_back_to_the_app_and_files_are_served(client):
    assert "<title>kestrel</title>" in client.get("/strategies").text
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/favicon.svg").text == "<svg></svg>"


def test_a_path_outside_the_build_is_never_served(client):
    response = client.get("/..%2F..%2Fpyproject.toml")
    assert "[project]" not in response.text


def test_the_api_works_without_a_built_front_end():
    client = TestClient(create_app(DEMO_PROFILE, clock=lambda: NOW, web_dist=None))
    assert client.get("/api/health").status_code == 200
    assert client.get("/").status_code == 404
````

`tests/test_read_only_guard.py`:

````python
"""kestrel shows money; it never moves it. This walks every module and fails on anything that could place,
change or cancel an order, or open a write route."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "kestrel"

FORBIDDEN_IMPORTS = ("trading_rails", "webull", "alpaca", "ib_insync", "ibapi", "robin_stocks", "schwab", "tda")
FORBIDDEN_CALLS = {"place", "place_order", "submit_order", "cancel", "cancel_order", "replace_order", "modify_order"}
FORBIDDEN_ROUTES = {"post", "put", "patch", "delete", "api_route", "add_api_route", "websocket"}


def modules():
    return sorted(SRC.rglob("*.py"))


def test_there_is_something_to_check():
    assert len(modules()) >= 8


def test_no_broker_or_trading_library_is_imported():
    offenders = []
    for path in modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            offenders += [f"{path.name}: {n}" for n in names if n.split(".")[0].lower() in FORBIDDEN_IMPORTS]
    assert not offenders, offenders


def test_nothing_calls_an_order_method_or_registers_a_write_route():
    offenders = []
    for path in modules():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                name = node.func.attr
                if name in FORBIDDEN_CALLS or name in FORBIDDEN_ROUTES:
                    offenders.append(f"{path.name}:{node.lineno} .{name}()")
    assert not offenders, offenders


def test_the_guard_catches_what_it_should():
    bad = ast.parse("broker.place_order(o)\napp.post('/x')\nimport webull.trade")
    calls = [n.func.attr for n in ast.walk(bad) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert "place_order" in calls and "post" in calls
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_server.py tests/test_read_only_guard.py -q`
Expected: `test_server.py` fails at import (`No module named 'kestrel.server'`). `test_read_only_guard.py` passes already. That's fine: it guards every later change.

- [ ] **Step 3: Implement**

`src/kestrel/server.py`:

````python
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
````


- [ ] **Step 4: Run them and watch them pass**

Run: `.venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check .`
Expected: everything passes (`test_server.py` 8, `test_read_only_guard.py` 4); ruff clean. A `StarletteDeprecationWarning` about httpx is expected and harmless.

- [ ] **Step 5: Commit**

```bash
git add src/kestrel/server.py tests/test_server.py tests/test_read_only_guard.py
git commit -m "feat(server): GET-only FastAPI app on 127.0.0.1 with an import/call guard"
```

---

### Task 7: The CLI, the generated files, and the contract doc

**Files:**
- Create: `src/kestrel/cli.py`, `docs/data-contract.md`
- Generate: `docs/contract/snapshot.schema.json`, `web/src/test/fixtures/home.json`, `web/src/test/fixtures/shell.json`
- Test: `tests/test_cli.py`, `tests/test_generated_files.py`

**Interfaces:**
- Produces: `kestrel serve [--profile P] [--port 8030] [--no-open]`, `kestrel check [--profile P]` (exit 0 ok, 1 when a source errors, 2 on a bad profile), `kestrel demo [--view snapshot|home|shell] [--now ISO]`, and `kestrel schema`. The two fixtures are the web tests' only data.

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:

````python
import json

from kestrel.cli import main

NOW = "2026-09-25T21:08:00+00:00"


def run(capsysbinary, *argv):
    code = main(list(argv))
    out, err = capsysbinary.readouterr()
    return code, out.decode("utf-8"), err.decode("utf-8")


def test_demo_prints_a_valid_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "demo", "--now", NOW)
    data = json.loads(out)
    assert code == 0 and data["contract_version"] == "1" and len(data["accounts"]) == 4


def test_demo_home_is_reproducible(capsysbinary):
    first = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    second = run(capsysbinary, "demo", "--view", "home", "--now", NOW)[1]
    assert first == second and json.loads(first)["summary"]["needs_you"] == 2


def test_schema_describes_the_snapshot(capsysbinary):
    code, out, _ = run(capsysbinary, "schema")
    schema = json.loads(out)
    assert code == 0 and schema["title"] == "Snapshot" and "accounts" in schema["properties"]


def test_check_passes_on_the_demo_and_fails_on_a_bad_profile(capsysbinary, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, out, _ = run(capsysbinary, "check")
    assert code == 0 and "hello, Alex" in out and "stale" in out
    bad = tmp_path / "bad.toml"
    bad.write_text('[app]\ntheme = "neon"\n', encoding="utf-8")
    code, _, err = run(capsysbinary, "check", "--profile", str(bad))
    assert code == 2 and "app.theme" in err


def test_check_fails_when_a_source_cannot_be_read(capsysbinary, tmp_path):
    profile = tmp_path / "p.toml"
    profile.write_text('[[sources]]\nid = "desk"\nkind = "feed"\n', encoding="utf-8")
    code, out, _ = run(capsysbinary, "check", "--profile", str(profile))
    assert code == 1 and "error" in out
````

`tests/test_generated_files.py`:

````python
"""Files generated from the code must match the code. Regenerate with the command in each failure message."""

import json
from pathlib import Path

import pytest

from kestrel.cli import main

ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-09-25T21:08:00+00:00"

GENERATED = [
    (ROOT / "docs" / "contract" / "snapshot.schema.json", ["schema"]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "home.json", ["demo", "--view", "home", "--now", NOW]),
    (ROOT / "web" / "src" / "test" / "fixtures" / "shell.json", ["demo", "--view", "shell", "--now", NOW]),
]


@pytest.mark.parametrize("path,argv", GENERATED, ids=[p.name for p, _ in GENERATED])
def test_generated_file_is_current(path, argv, capsysbinary):
    main(argv)
    current = json.loads(capsysbinary.readouterr().out.decode("utf-8"))
    command = "kestrel " + " ".join(argv) + f" > {path.relative_to(ROOT).as_posix()}"
    assert path.is_file(), f"missing: run `{command}`"
    assert json.loads(path.read_text(encoding="utf-8")) == current, f"out of date: run `{command}`"
````


- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/Scripts/python -m pytest tests/test_cli.py tests/test_generated_files.py -q`
Expected: `ModuleNotFoundError: No module named 'kestrel.cli'`.

- [ ] **Step 3: Implement the CLI and the doc**

`src/kestrel/cli.py`:

````python
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
````

`docs/data-contract.md`:

````markdown
# The kestrel data contract

Every source kestrel reads speaks one format: a **Snapshot**. The built-in connectors produce one, and so can any
system of your own — serve a Snapshot as JSON and the `feed` connector (Phase 4) plugs it in without a line of your
system's code entering this repo.

- **Schema:** [`contract/snapshot.schema.json`](contract/snapshot.schema.json), generated from
  `src/kestrel/contract.py` (`kestrel schema`); a test fails if the two drift.
- **A complete example:** `kestrel demo` prints the demo Snapshot — a year of fictional accounts, books, trades and runs.
- **Entities and fields:** the table in the [design spec](specs/2026-09-25-kestrel-design.md#7-data-contract-v1).

## Rules

- `contract_version` is `"1"`. Within a major version changes are **additive only**; kestrel ignores fields it does
  not know, and refuses an unknown major version (the source shows as `error` with the reason).
- Every timestamp carries an offset (`2026-09-25T17:08:00-04:00`); dates are `YYYY-MM-DD`.
- Money is in the profile's currency. `net_flow` on a value point is that day's deposits minus withdrawals, so
  performance is measured net of money moving in and out.
- `status` on a source is `ok`, `stale` or `error`; kestrel also marks a source stale once its `last_success` is older
  than the profile's `stale_after` for it.
- A connector only reads. Nothing in the contract asks a source to change anything.
````


- [ ] **Step 4: Reinstall so the `kestrel` command exists, then generate the files**

```bash
.venv/Scripts/python -m pip install -e ".[dev]"
mkdir -p docs/contract web/src/test/fixtures
.venv/Scripts/kestrel schema > docs/contract/snapshot.schema.json
.venv/Scripts/kestrel demo --view home --now 2026-09-25T21:08:00+00:00 > web/src/test/fixtures/home.json
.venv/Scripts/kestrel demo --view shell --now 2026-09-25T21:08:00+00:00 > web/src/test/fixtures/shell.json
.venv/Scripts/kestrel check
```

Expected `check` output (ASCII, exit 0):
```
profile: built-in demo profile - hello, Alex
  ok     Portfolio        data collector   2 minutes ago
  ok     Trading desk     feed             1 minute ago
  ok     Paper broker     rails            6 minutes ago
  stale  Savings          bank link        26 hours ago
```
`home.json` is about 48 KB and its `"summary"` reads `{"day_change": 6.7, "gap_pts": 2.94, "needs_you": 2}`.

- [ ] **Step 5: Run the whole suite**

Run: `.venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check .`
Expected: 71 passed; ruff clean.

- [ ] **Step 6: Commit**

```bash
git add src/kestrel/cli.py tests/test_cli.py tests/test_generated_files.py docs/data-contract.md docs/contract web/src/test/fixtures
git commit -m "feat(cli): serve, check, demo and schema; generated contract schema and web fixtures"
```

---

### Task 8: The web foundation: tokens, formatting, greeting, theme

**Files:**
- Create:
  - `web/package.json`, `web/index.html`, `web/public/favicon.svg`, `web/vite.config.ts`, `web/tsconfig.json`
  - `web/src/styles/tokens.css`
  - `web/src/test/setup.ts`
  - `web/src/lib/format.ts`, `web/src/lib/greeting.ts`, `web/src/lib/theme.ts`
- Test: `web/src/lib/format.test.ts`, `web/src/lib/greeting.test.ts`, `web/src/lib/theme.test.ts`, `web/src/styles/design.test.ts`

**Interfaces:**
- Produces:
  - **CSS tokens:** `--bg --side --panel --panel2 --line --line2 --ink1 --ink2 --ink3 --s1 --s2 --s3 --ref --warn --serious --good --up --down --acc --acc-ink --pad --row --k-sans --k-mono`, keyed off `data-theme / data-accent / data-gl / data-density` on the `.k` element, plus Tailwind colour utilities (`text-ink3`, `bg-panel2`, `border-line`, …).
  - **Classes:** `panel panel-title panel-sub label num seg icon-btn chip mark real paper expected badge up down tbl tip sr-only shell sidebar nav-item main topbar content grid12 span-{4,5,7,8,12} menu-btn tabbar scrim table-scroll hide-narrow ease`.
  - **`format.ts`:** `money signedMoney pct compactMoney num splitCents shortDate sinceLabel monthLabel timeHM ago setCurrency MINUS DASH`.
  - **`greeting.ts`:** `greeting(now, tz)`, `clockLine(now, tz)`.
  - **`theme.ts`:** `useTheme(pref) -> [theme, toggle]`, `resolveTheme`, `readOverride`.

- [ ] **Step 1: Scaffold the project and install**

`web/package.json`:

````json
{
  "name": "kestrel-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "@fontsource/geist": "^5.3.0",
    "@fontsource/geist-mono": "^5.3.0",
    "@tanstack/react-query": "^5.101.0",
    "@tanstack/react-router": "^1.170.0",
    "d3-array": "^3.2.4",
    "d3-scale": "^4.0.2",
    "d3-shape": "^3.2.0",
    "react": "^19.2.6",
    "react-dom": "^19.2.6"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.3.1",
    "@testing-library/react": "^16.3.0",
    "@types/d3-array": "^3.2.2",
    "@types/d3-scale": "^4.0.9",
    "@types/d3-shape": "^3.2.0",
    "@types/node": "^24.19.0",
    "@types/react": "^19.2.14",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.1",
    "jsdom": "^27.0.0",
    "tailwindcss": "^4.3.1",
    "typescript": "~6.0.2",
    "vite": "^8.0.12",
    "vitest": "^4.1.8"
  }
}
````

`web/index.html`:

````html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <title>kestrel</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
````

`web/public/favicon.svg`:

````svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#D46C38" d="M1.5 10.2c3.2-.4 6.4.2 9.2 1.6L12 9.4l1.3 2.4c2.8-1.4 6-2 9.2-1.6-2.9 1.4-5.6 3-7.6 5.2l-.6 5.1h-4.6l-.6-5.1c-2-2.2-4.7-3.8-7.6-5.2z"/></svg>
````

`web/vite.config.ts`:

````ts
/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://127.0.0.1:8030' }, // `kestrel serve --no-open` in another terminal
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
````

`web/tsconfig.json`:

````json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "skipLibCheck": true,
    "noEmit": true,
    "types": ["vite/client", "node"]
  },
  "include": ["src", "vite.config.ts"]
}
````

`web/src/test/setup.ts`:

````ts
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup())

// jsdom has no layout: give charts a width, and answer media queries with "no match".
// (Tests that opt into the node environment have no window at all.)
if (typeof window !== 'undefined') {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  globalThis.ResizeObserver ??= ResizeObserverStub as unknown as typeof ResizeObserver
  window.matchMedia ??= ((query: string) => ({
    matches: false, media: query, onchange: null,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
}
````


Run: `cd web && npm install`
Expected: `added ~157 packages`, and a new `web/package-lock.json` (commit it; CI runs `npm ci`).

- [ ] **Step 2: Write the failing tests**

`web/src/lib/format.test.ts`:

````ts
import { afterEach, describe, expect, it } from 'vitest'
import {
  ago, compactMoney, money, monthLabel, num, pct, setCurrency, shortDate, signedMoney, sinceLabel, splitCents, timeHM,
} from './format'

describe('money', () => {
  it('uses a true minus sign and cents', () => {
    expect(money(148392.18)).toBe('$148,392.18')
    expect(money(-12.3)).toBe('−$12.30')
    expect(money(118200, false)).toBe('$118,200')
  })
  it('signs deltas but never zero', () => {
    expect(signedMoney(412.3)).toBe('+$412.30')
    expect(signedMoney(-32.5)).toBe('−$32.50')
    expect(signedMoney(0)).toBe('$0.00')
    expect(signedMoney(-0.001)).toBe('$0.00')
  })
  it('splits the hero figure', () => {
    expect(splitCents(148392.18)).toEqual(['$148,392', '18'])
  })
  describe('in another currency', () => {
    afterEach(() => setCurrency('USD'))
    it('follows the profile', () => {
      setCurrency('EUR')
      expect(money(1234.5)).toBe('€1,234.50')
      expect(signedMoney(-2)).toBe('−€2.00')
      expect(splitCents(1234.5)).toEqual(['€1,234', '50'])
    })
  })
})

describe('numbers', () => {
  it('formats percents with a sign', () => {
    expect(pct(14.2)).toBe('+14.2%')
    expect(pct(-5.12)).toBe('−5.1%')
    expect(pct(0.04)).toBe('0.0%')
    expect(pct(0.279, 2)).toBe('+0.28%')
  })
  it('compacts chart labels', () => {
    expect(compactMoney(118200)).toBe('$118.2k')
    expect(compactMoney(1_250_000)).toBe('$1.3M')
    expect(compactMoney(-950)).toBe('−$950')
  })
  it('formats prices', () => {
    expect(num(508.2)).toBe('508.20')
    expect(num(-3)).toBe('−3.00')
  })
})

describe('dates', () => {
  it('formats short dates and axis labels', () => {
    expect(shortDate('2026-09-25')).toBe('Fri 25 Sep')
    expect(monthLabel('2026-09-25')).toBe('Sep')
    expect(monthLabel('2026-09-25', true)).toBe('25 Sep')
    expect(sinceLabel('2026-09-10', '2026-09-25T21:08:00Z')).toBe('10 Sep')
    expect(sinceLabel('2025-07-27', '2026-09-25T21:08:00Z')).toBe('Jul 2025')
  })
  it('formats times in the profile zone', () => {
    expect(timeHM('2026-09-25T21:08:00Z', 'America/New_York')).toBe('17:08')
  })
  it('says how long ago', () => {
    const now = new Date('2026-09-25T21:08:00Z')
    expect(ago('2026-09-25T21:06:00Z', now)).toBe('2m')
    expect(ago('2026-09-24T19:08:00Z', now)).toBe('26h')
    expect(ago('2026-09-20T21:08:00Z', now)).toBe('5d')
    expect(ago(null, now)).toBe('never')
  })
})
````

`web/src/lib/greeting.test.ts`:

````ts
import { describe, expect, it } from 'vitest'
import { clockLine, greeting } from './greeting'

const NY = 'America/New_York'

describe('greeting', () => {
  it('follows the profile time zone, not the computer', () => {
    expect(greeting(new Date('2026-09-25T13:00:00Z'), NY)).toBe('Good morning') // 09:00 in New York
    expect(greeting(new Date('2026-09-25T17:00:00Z'), NY)).toBe('Good afternoon') // 13:00
    expect(greeting(new Date('2026-09-25T21:08:00Z'), NY)).toBe('Good evening') // 17:08
    expect(greeting(new Date('2026-09-25T07:00:00Z'), NY)).toBe('Good evening') // 03:00
    expect(greeting(new Date('2026-09-25T21:08:00Z'), 'Asia/Tokyo')).toBe('Good morning') // 06:08
  })
  it('writes the clock line', () => {
    expect(clockLine(new Date('2026-09-25T21:08:00Z'), NY)).toBe('Fri 25 Sep · 17:08 EDT')
  })
})
````

`web/src/lib/theme.test.ts`:

````ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { readOverride, resolveTheme } from './theme'

describe('theme', () => {
  afterEach(() => vi.restoreAllMocks())

  it('resolves system against the OS setting', () => {
    expect(resolveTheme('system', true)).toBe('dark')
    expect(resolveTheme('system', false)).toBe('light')
    expect(resolveTheme('light', true)).toBe('light')
  })

  it('ignores junk and survives blocked storage', () => {
    window.localStorage.setItem('kestrel.theme', 'neon')
    expect(readOverride()).toBeNull()
    window.localStorage.setItem('kestrel.theme', 'light')
    expect(readOverride()).toBe('light')
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    expect(readOverride()).toBeNull()
  })
})
````

`web/src/styles/design.test.ts`:

````ts
// @vitest-environment node
// Design-system rules that code review keeps missing, pinned as tests (docs/design-system.md).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const SRC = fileURLToPath(new URL('..', import.meta.url))

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? files(path) : [path]
  })
}

describe('design rules', () => {
  it('components use tokens, never raw hex colours', () => {
    const offenders = files(SRC)
      .filter((f) => /\.tsx?$/.test(f) && !f.endsWith('.test.ts') && !f.endsWith('.test.tsx'))
      .filter((f) => /#[0-9a-fA-F]{3,8}\b/.test(readFileSync(f, 'utf8')))
    expect(offenders).toEqual([])
  })

  it('keeps screen-reader labels inside scrolling tables (no sideways page scroll on phones)', () => {
    const css = readFileSync(join(SRC, 'styles', 'tokens.css'), 'utf8')
    expect(css).toMatch(/\.table-scroll \{ position: relative;/)
    expect(css).toMatch(/\.panel \{ position: relative;/)
  })
})
````


- [ ] **Step 3: Run them and watch them fail**

Run (in `web/`): `npx vitest run`
Expected: the three `lib` suites fail to resolve `./format`, `./greeting` and `./theme`; `design.test.ts` fails because `tokens.css` doesn't exist.

- [ ] **Step 4: Implement**

`web/src/styles/tokens.css`:

````css
/* kestrel — Graphite design tokens. Source of truth: docs/design-system.md. Never use raw hex in components. */
@import "tailwindcss";

@theme inline {
  --color-bg: var(--bg);
  --color-side: var(--side);
  --color-panel: var(--panel);
  --color-panel2: var(--panel2);
  --color-line: var(--line);
  --color-line2: var(--line2);
  --color-ink1: var(--ink1);
  --color-ink2: var(--ink2);
  --color-ink3: var(--ink3);
  --color-acc: var(--acc);
  --color-acc-ink: var(--acc-ink);
  --color-up: var(--up);
  --color-down: var(--down);
  --color-warn: var(--warn);
  --color-serious: var(--serious);
  --color-good: var(--good);
  --font-sans: var(--k-sans);
  --font-mono: var(--k-mono);
}

.k {
  --bg: #0b0c0e; --side: #0e0f12; --panel: #121418; --panel2: #181b20; --line: #22262c; --line2: #2e333a;
  --ink1: #eceef1; --ink2: #a7adb6; --ink3: #7d848e;
  --s1: #5b93db; --s2: #d46c38; --s3: #8a9099; --ref: #7d848e;
  --warn: #e8b84b; --serious: #ec835a; --good: #4cc38f; --up: #4cc38f; --down: #ea5b60;
  --acc: #d46c38; --acc-ink: #e3875a; --on-acc: #0b0c0e;
  --pad: 20px; --row: 56px;
  --k-sans: "Geist", ui-sans-serif, system-ui, sans-serif;
  --k-mono: "Geist Mono", ui-monospace, monospace;
  color-scheme: dark;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink1);
  font-family: var(--k-sans);
  font-size: 14px;
  line-height: 1.4;
  -webkit-font-smoothing: antialiased;
}
.k[data-theme="light"] {
  --bg: #f2f3f5; --side: #f8f9fa; --panel: #ffffff; --panel2: #f5f6f8; --line: #e3e5e9; --line2: #d3d7dd;
  --ink1: #0f1114; --ink2: #4a5059; --ink3: #666d77;
  --s1: #2f6db5; --s2: #c45a24; --s3: #9aa0a8; --ref: #666d77;
  --warn: #9a6700; --serious: #c2562a; --good: #11845a; --up: #11845a; --down: #d1363b;
  color-scheme: light;
}
.k[data-accent="rufous"] { --acc: #d46c38; --acc-ink: #e3875a; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="rufous"] { --acc: #c45a24; --acc-ink: #a9481a; --on-acc: #ffffff; }
.k[data-accent="slate"] { --acc: #5b93db; --acc-ink: #7faae3; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="slate"] { --acc: #2f6db5; --acc-ink: #255a97; --on-acc: #ffffff; }
.k[data-accent="mono"] { --acc: #eceef1; --acc-ink: #eceef1; --on-acc: #0b0c0e; }
.k[data-theme="light"][data-accent="mono"] { --acc: #0f1114; --acc-ink: #0f1114; --on-acc: #ffffff; }
.k[data-gl="blue-orange"] { --up: #5b93db; --down: #d46c38; }
.k[data-theme="light"][data-gl="blue-orange"] { --up: #2f6db5; --down: #c45a24; }
.k[data-density="compact"] { --pad: 14px; --row: 44px; }

.k :focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
.k a { color: var(--ink2); text-decoration: none; }
.k a:hover { color: var(--ink1); }
@media (prefers-reduced-motion: no-preference) {
  .k .ease { transition: background-color 150ms ease-out, color 150ms ease-out, transform 150ms ease-out; }
}

/* --- building blocks ------------------------------------------------------------------------------------- */
.panel { position: relative; background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
  padding: var(--pad); display: flex; flex-direction: column; min-width: 0; height: var(--h, auto); }
.panel-title { font-size: 14px; font-weight: 600; letter-spacing: -0.005em; }
.panel-sub { font-size: 12px; color: var(--ink3); margin-top: 2px; }
.label { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink3); font-weight: 500; }
.num { font-family: var(--k-mono); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 7px; padding: 2px; gap: 2px;
  background: var(--panel); }
.seg button { font: 500 12px/1 var(--k-sans); padding: 6px 10px; border-radius: 5px; color: var(--ink3);
  cursor: pointer; background: none; border: 0; }
.seg button[aria-pressed="true"] { background: var(--panel2); color: var(--ink1); box-shadow: inset 0 0 0 1px var(--line2); }
.icon-btn { width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center;
  border-radius: 7px; border: 1px solid var(--line); color: var(--ink2); background: var(--panel); cursor: pointer; }
.chip { display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--ink2); padding: 5px 10px;
  border: 1px solid var(--line); border-radius: 999px; background: var(--panel); white-space: nowrap; }
.mark { width: 12px; height: 12px; border-radius: 3px; display: inline-block; flex: none; }
.mark.real { background: var(--mc, var(--ink2)); }
.mark.paper { background-image: repeating-linear-gradient(45deg, var(--mc, var(--ink2)) 0 1.5px, transparent 1.5px 4px);
  box-shadow: inset 0 0 0 1.25px var(--mc, var(--ink2)); }
.mark.expected { border: 1.5px dotted var(--mc, var(--ref)); }
.badge { display: inline-flex; align-items: center; gap: 6px; font: 600 10px/1 var(--k-mono); letter-spacing: 0.08em;
  color: var(--ink2); padding: 5px 7px; border: 1px solid var(--line2); border-radius: 5px; }
.up { color: var(--up); }
.down { color: var(--down); }
.tbl { width: 100%; border-collapse: collapse; }
.tbl th { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink3); font-weight: 500;
  text-align: left; padding: 0 12px 10px 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
.tbl td { height: var(--row); border-bottom: 1px solid var(--line); vertical-align: middle; padding: 0 12px 0 0; }
.tbl tr:last-child td { border-bottom: 0; }
.tbl .r { text-align: right; }
.tip { position: absolute; z-index: 10; pointer-events: none; background: var(--panel2); border: 1px solid var(--line2);
  border-radius: 7px; padding: 8px 10px; font-size: 12px; box-shadow: 0 8px 24px rgb(0 0 0 / 0.28); min-width: 170px; }
.sr-only { position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0; border: 0; overflow: hidden;
  clip: rect(0 0 0 0); white-space: nowrap; }

/* --- layout ------------------------------------------------------------------------------------------------ */
.shell { display: flex; min-height: 100vh; }
.sidebar { width: 256px; flex: none; height: 100vh; position: sticky; top: 0; background: var(--side);
  border-right: 1px solid var(--line); display: flex; flex-direction: column; padding: 18px 14px; overflow-y: auto; }
.nav-item { display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 10px; border-radius: 7px;
  font-size: 14px; font-weight: 500; color: var(--ink2); }
.nav-item[aria-current="page"] { background: var(--panel2); color: var(--ink1); box-shadow: inset 0 0 0 1px var(--line); }
.nav-item[aria-current="page"] svg { color: var(--acc); }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.topbar { height: 64px; flex: none; display: flex; align-items: center; gap: 10px; padding: 0 32px;
  border-bottom: 1px solid var(--line); }
.content { padding: 28px 32px 32px; }
.grid12 { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; align-content: start; }
.span-4 { grid-column: span 4; } .span-5 { grid-column: span 5; } .span-7 { grid-column: span 7; }
.span-8 { grid-column: span 8; } .span-12 { grid-column: span 12; }
.menu-btn, .tabbar, .scrim { display: none; }
/* position: relative keeps absolutely positioned children (sr-only labels) inside the scroll box */
.table-scroll { position: relative; overflow-x: auto; }

@media (max-width: 1180px) {
  .span-4, .span-5, .span-7, .span-8 { grid-column: span 12; }
  .panel { height: auto; }
}
@media (max-width: 900px) {
  .sidebar { position: fixed; left: 0; top: 0; z-index: 30; transform: translateX(-100%); }
  .shell[data-drawer="open"] .sidebar { transform: none; }
  .shell[data-drawer="open"] .scrim { display: block; position: fixed; inset: 0; z-index: 20; background: rgb(0 0 0 / 0.45); }
  .menu-btn { display: inline-flex; }
  .topbar { padding: 0 16px; }
  .content { padding: 20px 16px 24px; }
  .hide-narrow { display: none; }
}
@media (max-width: 640px) {
  .tabbar { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); position: fixed; left: 0; right: 0;
    bottom: 0; z-index: 25; height: 72px; padding: 6px 4px 14px; background: var(--side); border-top: 1px solid var(--line); }
  .content { padding-bottom: 96px; }
}
````

`web/src/lib/format.ts`:

````ts
// Number and date formatting. Rules: docs/design-system.md → "Numbers and copy".
export const MINUS = '−'
export const DASH = '—'

let currency = 'USD'
/** Set once from the profile; every money value then uses it. */
export function setCurrency(code: string): void {
  currency = code
}

function currencyFormat(cents: boolean): Intl.NumberFormat {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: cents ? 2 : 0,
    maximumFractionDigits: cents ? 2 : 0,
  })
}

/** $1,234.56 · −$12.30 (a true minus sign) */
export function money(value: number, cents = true): string {
  const text = currencyFormat(cents).format(Math.abs(value))
  return value < 0 && text !== currencyFormat(cents).format(0) ? MINUS + text : text
}

/** +$412.30 · −$32.50 · $0.00 (zero carries no sign) */
export function signedMoney(value: number, cents = true): string {
  const text = money(Math.abs(value), cents)
  if (text === money(0, cents)) return text
  return (value > 0 ? '+' : MINUS) + text
}

/** +14.2% · −5.1% · 0.0% */
export function pct(value: number, digits = 1): string {
  const text = Math.abs(value).toFixed(digits)
  if (Number(text) === 0) return `${text}%`
  return `${value > 0 ? '+' : MINUS}${text}%`
}

/** $118.2k · $1.2M — chart labels only */
export function compactMoney(value: number): string {
  const abs = Math.abs(value)
  const sign = value < 0 ? MINUS : ''
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}k`
  return `${sign}$${abs.toFixed(0)}`
}

/** 508.20 — prices and quantities */
export function num(value: number, digits = 2): string {
  const text = Math.abs(value).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
  return value < 0 ? MINUS + text : text
}

/** ["$148,392", "18"] — the hero figure dims its cents */
export function splitCents(value: number): [string, string] {
  const [whole, cents = '00'] = money(value).split('.')
  return [whole, cents]
}

/** "Fri 25 Sep" for an ISO date (YYYY-MM-DD) or timestamp, in the given zone */
export function shortDate(iso: string, timeZone = 'UTC'): string {
  const date = iso.length === 10 ? new Date(`${iso}T12:00:00Z`) : new Date(iso)
  const zone = iso.length === 10 ? 'UTC' : timeZone
  const parts = new Intl.DateTimeFormat('en-US', { weekday: 'short', day: 'numeric', month: 'short', timeZone: zone })
    .formatToParts(date)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('weekday')} ${get('day')} ${get('month')}`
}

/** "10 Sep" this year, "Sep 2025" before it — for "since" dates */
export function sinceLabel(iso: string, nowIso: string): string {
  const date = new Date(`${iso.slice(0, 10)}T12:00:00Z`)
  const month = date.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' })
  return date.getUTCFullYear() === new Date(nowIso).getUTCFullYear()
    ? `${date.getUTCDate()} ${month}`
    : `${month} ${date.getUTCFullYear()}`
}

/** "Sep" / "25 Sep" axis labels for an ISO date */
export function monthLabel(iso: string, withDay = false): string {
  const date = new Date(`${iso}T12:00:00Z`)
  const month = date.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' })
  return withDay ? `${date.getUTCDate()} ${month}` : month
}

/** 24-hour "17:08" in the given zone */
export function timeHM(iso: string, timeZone: string): string {
  return new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone })
    .format(new Date(iso))
}

/** "2 min ago" · "26 h ago" · "3 d ago" */
export function ago(iso: string | null, now: Date): string {
  if (!iso) return 'never'
  const minutes = Math.max(0, Math.floor((now.getTime() - new Date(iso).getTime()) / 60000))
  if (minutes < 60) return `${minutes}m`
  const hours = Math.floor(minutes / 60)
  if (hours < 48) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}
````

`web/src/lib/greeting.ts`:

````ts
/** "Good morning" (05–11), "Good afternoon" (12–16), otherwise "Good evening" — in the profile's time zone. */
export function greeting(now: Date, timeZone: string): string {
  const hour = Number(new Intl.DateTimeFormat('en-US', { hour: 'numeric', hourCycle: 'h23', timeZone }).format(now))
  if (hour >= 5 && hour < 12) return 'Good morning'
  if (hour >= 12 && hour < 17) return 'Good afternoon'
  return 'Good evening'
}

/** "Fri 25 Sep · 17:08 ET" style line under the greeting */
export function clockLine(now: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    timeZone, timeZoneName: 'short',
  }).formatToParts(now)
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('weekday')} ${get('day')} ${get('month')} · ${get('hour')}:${get('minute')} ${get('timeZoneName')}`
}
````

`web/src/lib/theme.ts`:

````ts
import { useEffect, useState } from 'react'

export type ThemePref = 'system' | 'dark' | 'light'
export type Theme = 'dark' | 'light'

const KEY = 'kestrel.theme' // a per-viewer convenience; the profile sets the default

export function resolveTheme(pref: ThemePref, prefersDark: boolean): Theme {
  if (pref === 'system') return prefersDark ? 'dark' : 'light'
  return pref
}

export function readOverride(): Theme | null {
  try {
    const value = window.localStorage.getItem(KEY)
    return value === 'dark' || value === 'light' ? value : null
  } catch {
    return null // private windows and blocked storage: fall back to the profile
  }
}

function saveOverride(theme: Theme): void {
  try {
    window.localStorage.setItem(KEY, theme)
  } catch {
    // not fatal: the toggle still works for this visit
  }
}

function systemPrefersDark(): boolean {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** The theme to render and a toggle. Order: the viewer's toggle, then the profile, then the system. */
export function useTheme(pref: ThemePref): [Theme, () => void] {
  const [prefersDark, setPrefersDark] = useState(systemPrefersDark)
  const [override, setOverride] = useState<Theme | null>(readOverride)
  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => setPrefersDark(query.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])
  const theme = override ?? resolveTheme(pref, prefersDark)
  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    saveOverride(next)
    setOverride(next)
  }
  return [theme, toggle]
}
````


- [ ] **Step 5: Run them and watch them pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit`
Expected: `Test Files 4 passed`, `Tests 16 passed`; tsc prints nothing.

- [ ] **Step 6: Commit**

```bash
git add web/package.json web/package-lock.json web/index.html web/public web/vite.config.ts web/tsconfig.json web/src/styles web/src/test/setup.ts web/src/lib/format.ts web/src/lib/format.test.ts web/src/lib/greeting.ts web/src/lib/greeting.test.ts web/src/lib/theme.ts web/src/lib/theme.test.ts
git commit -m "feat(web): Graphite tokens, number/date formatting, greeting and theme"
```

---

### Task 9: The shell and routing

**Files:**
- Create:
  - `web/src/lib/api.ts`
  - `web/src/components/Icon.tsx`, `web/src/components/bits.tsx`
  - `web/src/shell/Shell.tsx`
  - `web/src/pages/Soon.tsx`
  - `web/src/pages/home/Home.tsx` (first version: title and summary sentence only)
  - `web/src/router.tsx`, `web/src/main.tsx`
  - `web/src/test/renderApp.tsx`
- Test: `web/src/shell/Shell.test.tsx`

**Interfaces:**
- Consumes: Task 8's tokens and libs; the fixtures from Task 7.
- Produces:
  - **`api.ts`:** types mirroring the Python views, plus `getJson`, `useShell()` and `useHome()` (query keys `['shell']` / `['home']`, refetched every 60 s).
  - **`Icon`** (`name: IconName`) and **`Mark`**.
  - **`bits.tsx`:** `BookMark({kind, color?, size?})`, `MoneyBadge`, `Delta({value})`, `Panel({id, title, subtitle?, actions?, span, height?})`, `Seg({label, options, value, onChange})`, `Missing`.
  - **Routing:** `createAppRouter(history?)`; `NAV` in `Shell.tsx`.
  - **Tests:** `renderApp(path, data?)` returns `{ router, client, ... }` with the network stubbed off.
  - **Theming:** the Shell puts `.k` and the `data-*` theme attributes on `<html>`.

- [ ] **Step 1: Write the failing test and its harness**

`web/src/test/renderApp.tsx`:

````tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryHistory, RouterProvider } from '@tanstack/react-router'
import { render } from '@testing-library/react'
import { vi } from 'vitest'
import type { HomeView, ShellView } from '../lib/api'
import { createAppRouter } from '../router'
import homeJson from './fixtures/home.json'
import shellJson from './fixtures/shell.json'

// Generated by `kestrel demo --view ...`; tests/test_generated_files.py keeps them in step with the Python code.
export const homeFixture = homeJson as unknown as HomeView
export const shellFixture = shellJson as unknown as ShellView

/** The whole app at `path`, with the API answered from fixtures. Any real network call fails the test. */
export function renderApp(path = '/', data: { home?: HomeView; shell?: ShellView } = {}) {
  vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('network is off in tests'))))
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } })
  client.setQueryData(['home'], data.home ?? homeFixture)
  client.setQueryData(['shell'], data.shell ?? shellFixture)
  const router = createAppRouter(createMemoryHistory({ initialEntries: [path] }))
  const view = render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...view, router, client }
}
````

`web/src/shell/Shell.test.tsx`:

````tsx
import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { renderApp, shellFixture } from '../test/renderApp'

describe('shell', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('greets by name in the profile time zone', async () => {
    renderApp('/')
    expect(await screen.findByText('Good evening,')).toBeTruthy() // 17:08 in New York
    expect(screen.getByText('Alex')).toBeTruthy()
  })

  it('lists every source and flags the stale one without relying on colour', async () => {
    renderApp('/')
    const sidebar = await screen.findByRole('complementary', { name: 'Sidebar' })
    expect(within(sidebar).getByText('Savings')).toBeTruthy()
    expect(within(sidebar).getByText('26h')).toBeTruthy()
    expect(within(sidebar).getAllByText('stale')).toHaveLength(1)
  })

  it('marks the current page and navigates', async () => {
    renderApp('/')
    const nav = await screen.findByRole('navigation', { name: 'Main' })
    expect(within(nav).getByRole('link', { name: /Home/ }).getAttribute('aria-current')).toBe('page')
    fireEvent.click(within(nav).getByRole('link', { name: /Strategies/ }))
    expect(await screen.findByText(/Phase 3/)).toBeTruthy()
    expect(within(nav).getByRole('link', { name: /Strategies/ }).getAttribute('aria-current')).toBe('page')
  })

  it('themes the whole document from the profile, and the toggle flips it', async () => {
    renderApp('/', { shell: { ...shellFixture, app: { ...shellFixture.app, theme: 'light', accent: 'slate' } } })
    await screen.findByText('Alex')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(document.documentElement.dataset.accent).toBe('slate')
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }))
    expect(document.documentElement.dataset.theme).toBe('dark')
    window.localStorage.clear()
  })

  it('shows an unknown path as not found inside the shell', async () => {
    renderApp('/nowhere')
    expect(await screen.findByRole('heading', { name: 'Not found' })).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeTruthy()
  })
})
````


- [ ] **Step 2: Run it and watch it fail**

Run (in `web/`): `npx vitest run src/shell`
Expected: fails to resolve `../lib/api` / `../router`.

- [ ] **Step 3: Implement**

`web/src/lib/api.ts`:

````ts
// Types mirror src/kestrel/views/*.py. The fixtures in src/test/fixtures are generated from the Python code and a
// Python test fails when they drift, so a renamed field shows up as a failing front-end test here.
import { useQuery } from '@tanstack/react-query'

export type Money = 'real' | 'paper'
export type Level = 'serious' | 'warning' | 'note'

export interface AppSettings {
  name: string
  accent: 'rufous' | 'slate' | 'mono'
  theme: 'system' | 'dark' | 'light'
  gain_loss: 'green-red' | 'blue-orange'
  density: 'comfortable' | 'compact'
  currency: string
  timezone: string
}

export interface Source {
  id: string
  label: string
  kind: string
  last_success: string | null
  status: 'ok' | 'stale' | 'error'
  detail: string
}

export interface ShellView {
  name: string
  app: AppSettings
  benchmark_label: string
  now: string
  sources: Source[]
  counts: { accounts: number; books: number; strategies: number }
}

export interface Delta {
  amount: number
  pct: number | null
}

export interface ValuePoint {
  date: string
  value: number
  net_flow: number
}

export interface NetWorth {
  total: number
  today: Delta
  month: Delta
  year: Delta
  year_flows: number
  points: ValuePoint[]
}

export interface Slice {
  category: string
  label: string
  value: number
  share: number
  cells: number
}

export interface AccountRow {
  id: string
  name: string
  category: string
  value: number
  day_pct: number | null
}

export interface Line {
  key: 'trading' | 'long_term' | 'benchmark'
  label: string
  return_pct: number
  max_drop_pct: number
  values: (number | null)[]
}

export interface Comparison {
  window: 'ytd' | '12m'
  dates: string[]
  lines: Line[]
  gap_pts: number | null
  shallower: boolean | null
  real_trades: number
  review_at: number | null
}

export interface Attention {
  level: Level
  title: string
  detail: string
  link: string
}

export interface BookRow {
  id: string
  name: string
  strategy: string
  money: Money
  status: string
  value: number
  day_change: number | null
  since_pct: number | null
  started: string
  trades: number
  per_trade_pct: number | null
  band_lo: number | null
  band_hi: number | null
  verdict: 'in_band' | 'below' | 'above' | 'early' | 'none'
  slots_used: number
  slots_total: number | null
  next_run: string | null
}

export interface TodayRun {
  time: string
  label: string
  status: 'done' | 'due' | 'late' | 'failed' | 'paused'
  detail: string
}

export interface PositionRow {
  book_id: string
  book: string
  symbol: string
  money: Money
  quantity: number
  entry_price: number
  last_price: number
  stop_price: number | null
  room_pct: number | null
  pnl: number
  note: string
}

export interface HomeView {
  as_of: string
  summary: { day_change: number; gap_pts: number | null; needs_you: number }
  net_worth: NetWorth
  allocation: Slice[]
  accounts: AccountRow[]
  comparison: Comparison
  attention: Attention[]
  books: BookRow[]
  today: TodayRun[]
  positions: PositionRow[]
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`${path} answered ${response.status}`)
  return (await response.json()) as T
}

const MINUTE = 60_000

export function useShell() {
  return useQuery({ queryKey: ['shell'], queryFn: () => getJson<ShellView>('/api/shell'), refetchInterval: MINUTE })
}

export function useHome() {
  return useQuery({ queryKey: ['home'], queryFn: () => getJson<HomeView>('/api/home'), refetchInterval: MINUTE })
}
````

`web/src/components/Icon.tsx`:

````tsx
// Stroke icons on a 24 px grid, 1.75 stroke, round caps (docs/design-system.md → Icons). Never emoji.
import type { CSSProperties, ReactElement } from 'react'

const PATHS: Record<string, ReactElement> = {
  home: <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6h-4v6H5a1 1 0 0 1-1-1z" />,
  accounts: (<><rect x="3" y="6" width="18" height="14" rx="2" /><path d="M3 10h18" /><path d="M16 15h2" /></>),
  books: (<><path d="m12 3 9 5-9 5-9-5z" /><path d="m3 13 9 5 9-5" /></>),
  strategy: (<><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" />
    <path d="M8.5 6H15a3 3 0 0 1 0 6H9a3 3 0 0 0 0 6h6.5" /></>),
  backtests: (<><path d="M9 3h6" /><path d="M10 3v6L4.5 18.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3" />
    <path d="M7 15h10" /></>),
  activity: <path d="M3 12h4l2.5-6 5 12 2.5-6h4" />,
  settings: (<><path d="M4 7h10" /><path d="M18 7h2" /><path d="M4 17h4" /><path d="M12 17h8" />
    <circle cx="16" cy="7" r="2" /><circle cx="10" cy="17" r="2" /></>),
  refresh: (<><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 5v6h-6" /></>),
  moon: <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />,
  sun: (<><circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>),
  chevron: <path d="m9 6 6 6-6 6" />,
  arrow: (<><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>),
  alert: (<><path d="M12 4 2.8 19.5a1 1 0 0 0 .9 1.5h16.6a1 1 0 0 0 .9-1.5z" /><path d="M12 10v4" /><path d="M12 17.5h.01" /></>),
  shield: (<><path d="M12 3 5 6v5c0 4.5 3 8.3 7 10 4-1.7 7-5.5 7-10V6z" /><path d="m9.5 9.5 5 5" /><path d="m14.5 9.5-5 5" /></>),
  clock: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  info: (<><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>),
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  checkCircle: (<><circle cx="12" cy="12" r="9" /><path d="m8 12.5 3 3 5-6" /></>),
  circle: <circle cx="12" cy="12" r="8" />,
  menu: (<><path d="M4 7h16" /><path d="M4 12h16" /><path d="M4 17h16" /></>),
  panel: (<><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M9 4v16" /></>),
  more: (<><path d="M5 12h.01" /><path d="M12 12h.01" /><path d="M19 12h.01" /></>),
  scale: (<><path d="M12 4v16" /><path d="M5 8h14" /><path d="m5 8-2.5 6a3 3 0 0 0 5 0z" />
    <path d="m19 8-2.5 6a3 3 0 0 0 5 0z" /><path d="M8 20h8" /></>),
}

export type IconName = keyof typeof PATHS

export function Icon({ name, size = 16, style }: { name: IconName; size?: number; style?: CSSProperties }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flex: 'none', ...style }}>
      {PATHS[name]}
    </svg>
  )
}

/** The kestrel mark: a hovering bird, in the accent colour. */
export function Mark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" style={{ flex: 'none' }}>
      <path fill="var(--acc)" d="M1.5 10.2c3.2-.4 6.4.2 9.2 1.6L12 9.4l1.3 2.4c2.8-1.4 6-2 9.2-1.6-2.9 1.4-5.6 3-7.6 5.2l-.6 5.1h-4.6l-.6-5.1c-2-2.2-4.7-3.8-7.6-5.2z" />
    </svg>
  )
}
````

`web/src/components/bits.tsx`:

````tsx
// Small shared pieces: the money-state mark and badge, deltas, panels, segmented controls.
import type { CSSProperties, ReactNode } from 'react'
import type { Money } from '../lib/api'

/** Real = solid, paper = hatched, expected = dotted. The one convention every page shares. */
export function BookMark({ kind, color, size = 12 }: { kind: Money | 'expected'; color?: string; size?: number }) {
  return (
    <span className={`mark ${kind}`} aria-hidden="true"
      style={{ width: size, height: size, ...(color ? ({ '--mc': color } as CSSProperties) : {}) }} />
  )
}

export function MoneyBadge({ money }: { money: Money }) {
  return <span className="badge"><BookMark kind={money} size={9} />{money === 'real' ? 'REAL' : 'PAPER'}</span>
}

/** A signed value with ▲/▼ so a gain or loss never rests on colour alone. */
export function Delta({ value, children }: { value: number; children: ReactNode }) {
  if (Math.abs(value) < 0.005) return <span className="num" style={{ color: 'var(--ink3)' }}>{children}</span>
  const up = value > 0
  return (
    <span className={`num ${up ? 'up' : 'down'}`}>
      <span aria-hidden="true">{up ? '▲' : '▼'} </span>
      <span className="sr-only">{up ? 'up ' : 'down '}</span>
      {children}
    </span>
  )
}

export function Panel({ id, title, subtitle, actions, span, height, children }: {
  id: string; title: string; subtitle?: string; actions?: ReactNode; span: 4 | 5 | 7 | 8 | 12; height?: number
  children: ReactNode
}) {
  return (
    <section className={`panel span-${span}`} aria-labelledby={`${id}-title`}
      style={height ? ({ '--h': `${height}px` } as CSSProperties) : undefined}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={`${id}-title`} className="panel-title">{title}</h2>
          {subtitle && <div className="panel-sub">{subtitle}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
      {children}
    </section>
  )
}

export function Seg<T extends string>({ label, options, value, onChange }: {
  label: string; options: readonly T[]; value: T; onChange: (value: T) => void
}) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((option) => (
        <button key={option} type="button" aria-pressed={option === value} onClick={() => onChange(option)}>
          {option}
        </button>
      ))}
    </div>
  )
}

/** "—" for a missing value (design-system rule), in muted ink */
export function Missing() {
  return <span style={{ color: 'var(--ink3)' }}>—</span>
}
````

`web/src/shell/Shell.tsx`:

````tsx
// The frame around every page: sidebar (greeting, navigation, sources), top bar, phone tab bar.
import { useQueryClient } from '@tanstack/react-query'
import { Link, Outlet, useRouterState } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Icon, type IconName, Mark } from '../components/Icon'
import { type ShellView, type Source, useShell } from '../lib/api'
import { ago, setCurrency, timeHM } from '../lib/format'
import { clockLine, greeting } from '../lib/greeting'
import { useTheme } from '../lib/theme'

type CountKey = keyof ShellView['counts']
interface NavItem { to: string; label: string; icon: IconName; count?: CountKey }

export const NAV: { group: string; items: NavItem[] }[] = [
  { group: 'Overview', items: [{ to: '/', label: 'Home', icon: 'home' }] },
  { group: 'Money', items: [{ to: '/accounts', label: 'Accounts', icon: 'accounts', count: 'accounts' }] },
  {
    group: 'Trading',
    items: [
      { to: '/books', label: 'Books', icon: 'books', count: 'books' },
      { to: '/strategies', label: 'Strategies', icon: 'strategy', count: 'strategies' },
    ],
  },
  { group: 'Research', items: [{ to: '/backtests', label: 'Backtests', icon: 'backtests' }] },
  {
    group: 'System',
    items: [
      { to: '/activity', label: 'Activity', icon: 'activity' },
      { to: '/settings', label: 'Settings', icon: 'settings' },
    ],
  },
]

const TABS: NavItem[] = [
  { to: '/', label: 'Home', icon: 'home' },
  { to: '/accounts', label: 'Accounts', icon: 'accounts' },
  { to: '/books', label: 'Books', icon: 'books' },
  { to: '/strategies', label: 'Strategies', icon: 'strategy' },
  { to: '/settings', label: 'More', icon: 'more' },
]

function crumbs(pathname: string): [string, string] {
  for (const { group, items } of NAV) {
    const item = items.find((i) => i.to === pathname)
    if (item) return [group, item.label]
  }
  return ['kestrel', 'Not found']
}

const STATUS_ICON: Record<Source['status'], { name: IconName; color: string; text: string }> = {
  ok: { name: 'checkCircle', color: 'var(--good)', text: 'up to date' },
  stale: { name: 'clock', color: 'var(--warn)', text: 'stale' },
  error: { name: 'alert', color: 'var(--serious)', text: 'error' },
}

function SourceRow({ source, now }: { source: Source; now: Date }) {
  const status = STATUS_ICON[source.status]
  return (
    <div className="flex items-center gap-2.5 h-7 text-xs" title={source.detail || undefined}>
      <Icon name={status.name} size={14} style={{ color: status.color }} />
      <span className="text-ink2">{source.label}</span>
      <span className="text-ink3 text-[11px] truncate">{source.kind}</span>
      <span className="sr-only">{status.text}</span>
      <span className="num ml-auto text-[11px]" style={{ color: source.status === 'ok' ? 'var(--ink3)' : status.color }}>
        {ago(source.last_success, now)}
      </span>
    </div>
  )
}

function Sidebar({ shell }: { shell?: ShellView }) {
  const now = shell ? new Date(shell.now) : null
  const tz = shell?.app.timezone ?? 'UTC'
  return (
    <aside className="sidebar" aria-label="Sidebar">
      <div className="flex items-center gap-2.5 px-1.5 h-9">
        <Mark />
        <span className="text-base font-semibold tracking-tight">{shell?.app.name ?? 'kestrel'}</span>
      </div>
      <div className="px-2 pt-6 pb-2">
        <div className="text-[13px] text-ink3">{now ? `${greeting(now, tz)},` : ' '}</div>
        <div className="text-[26px] font-semibold tracking-[-0.03em] mt-0.5">{shell?.name ?? ' '}</div>
        <div className="num text-[11px] text-ink3 mt-1.5">{now ? clockLine(now, tz) : ' '}</div>
      </div>
      <nav aria-label="Main" className="flex flex-col gap-0.5">
        {NAV.map(({ group, items }) => (
          <div key={group} className="flex flex-col gap-0.5">
            <div className="label px-2.5 pt-4 pb-1.5">{group}</div>
            {items.map((item) => (
              <Link key={item.to} to={item.to} className="nav-item ease"
                activeOptions={{ exact: item.to === '/' }} activeProps={{ 'aria-current': 'page' }}>
                <Icon name={item.icon} size={17} />
                <span>{item.label}</span>
                {item.count && shell && <span className="num ml-auto text-[11px] text-ink3">{shell.counts[item.count]}</span>}
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div className="mt-auto border-t border-line pt-3.5 px-1.5">
        <div className="label mb-1.5">Sources</div>
        {now && shell?.sources.map((s) => <SourceRow key={s.id} source={s} now={now} />)}
      </div>
    </aside>
  )
}

function TopBar({ pathname, shell, theme, onToggleTheme, onMenu }: {
  pathname: string; shell?: ShellView; theme: 'dark' | 'light'; onToggleTheme: () => void; onMenu: () => void
}) {
  const client = useQueryClient()
  const [group, page] = crumbs(pathname)
  return (
    <header className="topbar">
      <button type="button" className="icon-btn menu-btn" aria-label="Open menu" onClick={onMenu}>
        <Icon name="menu" size={18} />
      </button>
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-[13px]">
        <span className="text-ink3 hide-narrow">{group}</span>
        <Icon name="chevron" size={14} style={{ color: 'var(--ink3)' }} />
        <span className="font-medium">{page}</span>
      </nav>
      <div className="ml-auto flex items-center gap-3">
        {shell && (
          <span className="text-xs text-ink3 hide-narrow">Updated {timeHM(shell.now, shell.app.timezone)}</span>
        )}
        <button type="button" className="icon-btn" aria-label="Refresh data" onClick={() => client.invalidateQueries()}>
          <Icon name="refresh" size={16} />
        </button>
        <button type="button" className="icon-btn" onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={16} />
        </button>
      </div>
    </header>
  )
}

function TabBar() {
  return (
    <nav className="tabbar" aria-label="Tabs">
      {TABS.map((tab) => (
        <Link key={tab.to} to={tab.to} activeOptions={{ exact: tab.to === '/' }} activeProps={{ 'aria-current': 'page' }}
          className="flex flex-col items-center justify-center gap-1 min-h-12 text-[11px] font-medium text-ink3 aria-[current=page]:text-ink1">
          <Icon name={tab.icon} size={20} />
          {tab.label}
        </Link>
      ))}
    </nav>
  )
}

export function Shell() {
  const shell = useShell()
  const app = shell.data?.app
  const [theme, toggleTheme] = useTheme(app?.theme ?? 'system')
  const [drawer, setDrawer] = useState(false)
  const pathname = useRouterState({ select: (s) => s.location.pathname })

  useEffect(() => setDrawer(false), [pathname]) // navigating closes the phone drawer
  useEffect(() => {
    if (app) setCurrency(app.currency)
    document.title = app?.name ?? 'kestrel'
  }, [app])
  useEffect(() => {
    // theme the whole document so overscroll and scrollbars match
    const root = document.documentElement
    root.classList.add('k')
    root.dataset.theme = theme
    root.dataset.accent = app?.accent ?? 'rufous'
    root.dataset.gl = app?.gain_loss ?? 'green-red'
    root.dataset.density = app?.density ?? 'comfortable'
  }, [theme, app])

  return (
    <div className="shell" data-drawer={drawer ? 'open' : 'closed'}>
      <Sidebar shell={shell.data} />
      <div className="scrim" aria-hidden="true" onClick={() => setDrawer(false)} />
      <div className="main">
        <TopBar pathname={pathname} shell={shell.data} theme={theme} onToggleTheme={toggleTheme}
          onMenu={() => setDrawer(true)} />
        <main className="content" id="main">
          {shell.isError && (
            <div role="alert" className="panel mb-4" style={{ borderColor: 'var(--serious)' }}>
              kestrel&rsquo;s server didn&rsquo;t answer. Is <code>kestrel serve</code> running?
            </div>
          )}
          <Outlet />
        </main>
      </div>
      <TabBar />
    </div>
  )
}
````

`web/src/pages/Soon.tsx`:

````tsx
import { Mark } from '../components/Icon'

/** An honest placeholder for a page a later phase builds. */
export function Soon({ title, text }: { title: string; text: string }) {
  return (
    <div>
      <h1 className="text-[28px] font-semibold tracking-[-0.025em]">{title}</h1>
      <div className="panel mt-5 items-center text-center py-16 gap-3">
        <Mark size={28} />
        <p className="text-ink2 max-w-md">{text}</p>
      </div>
    </div>
  )
}
````

`web/src/pages/home/Home.tsx`:

````tsx
import { Delta } from '../../components/bits'
import { type HomeView, useHome } from '../../lib/api'
import { signedMoney } from '../../lib/format'

/** The sentence under the page title, written from the data. */
export function summaryParts(h: HomeView): { trading: string | null; needs: string } {
  const gap = h.summary.gap_pts
  const period = h.comparison.window === 'ytd' ? 'this year' : 'over the past 12 months'
  const trading = gap == null ? null : Math.abs(gap) < 0.05
    ? `Trading is level with your index money ${period}.`
    : `Trading is ${gap > 0 ? 'ahead of' : 'behind'} your index money by ${Math.abs(gap).toFixed(1)} pts ${period}.`
  const n = h.summary.needs_you
  const needs = n === 0 ? 'Nothing needs you.' : n === 1 ? 'One item needs you.' : `${n} items need you.`
  return { trading, needs }
}

export function Home() {
  const home = useHome()
  if (home.isPending) {
    return <p className="text-ink3" role="status">Loading your money…</p>
  }
  if (home.isError) {
    return <div role="alert" className="panel">Home couldn&rsquo;t load: {home.error.message}</div>
  }
  const h = home.data
  const { trading, needs } = summaryParts(h)
  return (
    <header className="mb-5">
      <h1 className="text-[28px] font-semibold tracking-[-0.025em]">Home</h1>
      <p className="text-ink2 mt-1.5">
        All your money is <Delta value={h.summary.day_change}>{signedMoney(h.summary.day_change)}</Delta> today.{' '}
        {trading && <>{trading} </>}{needs}
      </p>
    </header>
  )
}
````

`web/src/router.tsx`:

````tsx
import { createRootRoute, createRoute, createRouter, type RouterHistory } from '@tanstack/react-router'
import { Home } from './pages/home/Home'
import { Soon } from './pages/Soon'
import { Shell } from './shell/Shell'

const root = createRootRoute({
  component: Shell,
  notFoundComponent: () => <Soon title="Not found" text="There is no page here. Pick one from the menu." />,
})

const later = (path: string, title: string, text: string) =>
  createRoute({ getParentRoute: () => root, path, component: () => <Soon title={title} text={text} /> })

const routeTree = root.addChildren([
  createRoute({ getParentRoute: () => root, path: '/', component: Home }),
  later('/accounts', 'Accounts', 'Every account, what it holds, and how much of its growth was your deposits — Phase 4.'),
  later('/books', 'Books', 'Each book, real or paper: equity against its benchmark, drawdown, trades — Phase 3.'),
  later('/strategies', 'Strategies', 'How each strategy trades and whether it is behaving as its backtest said — Phase 3.'),
  later('/backtests', 'Backtests', 'What has been tested and what passed — Phase 5.'),
  later('/activity', 'Activity', 'What ran, what is due, what failed — Phase 5.'),
  later('/settings', 'Settings', 'Your profile and the status of every source — Phase 5.'),
])

export function createAppRouter(history?: RouterHistory) {
  return createRouter({ routeTree, history, defaultPreload: 'intent' })
}
````

`web/src/main.tsx`:

````tsx
import '@fontsource/geist/latin-400.css'
import '@fontsource/geist/latin-500.css'
import '@fontsource/geist/latin-600.css'
import '@fontsource/geist-mono/latin-400.css'
import '@fontsource/geist-mono/latin-500.css'
import '@fontsource/geist-mono/latin-600.css'
import './styles/tokens.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createAppRouter } from './router'

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } })
const router = createAppRouter()

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
````


- [ ] **Step 4: Run everything and watch it pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit && npm run build`
Expected: `Test Files 5 passed`, `Tests 21 passed`; tsc clean; `✓ built`.

- [ ] **Step 5: Commit**

```bash
git add web/src
git commit -m "feat(web): shell with greeting, grouped navigation, source freshness, theme and phone drawer"
```

---

### Task 10: The Home page and the chart kit

**Files:**
- Create:
  - `web/src/charts/geometry.ts`, `web/src/charts/LineChart.tsx`
  - `web/src/pages/home/NetWorthPanel.tsx`, `AllocationPanel.tsx`, `ComparisonPanel.tsx`, `AttentionPanel.tsx`, `BooksPanel.tsx`, `TodayAndPositions.tsx`
- Modify: `web/src/pages/home/Home.tsx` (replace with the full page)
- Test: `web/src/charts/geometry.test.ts`, `web/src/pages/home/Home.test.tsx`

**Interfaces:**
- Consumes: everything from Task 9.
- Produces:
  - **`geometry.ts`:** `windowPoints(points, range)`, `baseline(points)`, `nearestIndex(xs, x)`, `tickIndices(n, count)`, `RANGES`.
  - **`LineChart.tsx`:** `LineChart({dates, series, height, ariaLabel, yFormat, valueFormat, xLabel, tipTitle, zeroLine?, compact?})`, where `series[].style` is `'solid' | 'dashed' | 'dotted'`; and `LineKey`.
  - **Home helpers:** `verdict(comparison)` and `summaryParts(home)`.

- [ ] **Step 1: Write the failing tests**

`web/src/charts/geometry.test.ts`:

````ts
import { describe, expect, it } from 'vitest'
import type { ValuePoint } from '../lib/api'
import { baseline, nearestIndex, tickIndices, windowPoints } from './geometry'

const p = (date: string, value: number, net_flow = 0): ValuePoint => ({ date, value, net_flow })

describe('chart geometry', () => {
  it('keeps the points inside a range', () => {
    const pts = [p('2025-12-31', 1), p('2026-01-02', 2), p('2026-08-24', 3), p('2026-09-25', 4)]
    expect(windowPoints(pts, 'YTD').map((x) => x.date)).toEqual(['2026-01-02', '2026-08-24', '2026-09-25'])
    expect(windowPoints(pts, '1M').map((x) => x.date)).toEqual(['2026-08-24', '2026-09-25']) // 25 Aug is outside
    expect(windowPoints([p('2026-09-25', 4)], '1M')).toHaveLength(1)
    expect(windowPoints([], '1Y')).toEqual([])
  })
  it('never returns fewer than two points when it has them', () => {
    const pts = [p('2026-01-02', 1), p('2026-09-24', 2), p('2026-09-25', 3)]
    expect(windowPoints(pts, '1M')).toHaveLength(2)
  })
  it('adds deposits onto the starting value', () => {
    expect(baseline([p('a', 100), p('b', 130, 20), p('c', 90, -10)])).toEqual([100, 120, 110])
  })
  it('finds the nearest x', () => {
    expect(nearestIndex([0, 10, 20], 14)).toBe(1)
    expect(nearestIndex([0, 10, 20], 16)).toBe(2)
    expect(nearestIndex([0, 10, 20], -5)).toBe(0)
    expect(nearestIndex([], 3)).toBe(-1)
  })
  it('spreads ticks', () => {
    expect(tickIndices(262, 6)).toEqual([0, 52, 104, 157, 209, 261])
    expect(tickIndices(3, 6)).toEqual([0, 1, 2])
  })
})
````

`web/src/pages/home/Home.test.tsx`:

````tsx
import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { HomeView } from '../../lib/api'
import { homeFixture, renderApp } from '../../test/renderApp'
import { verdict } from './ComparisonPanel'
import { summaryParts } from './Home'

const panel = (name: string) => screen.getByRole('region', { name })

describe('Home', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('leads with net worth, cents dimmed', async () => {
    renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    const [whole, cents] = homeFixture.net_worth.total.toFixed(2).split('.')
    expect(within(nw).getByText(`$${Number(whole).toLocaleString('en-US')}`)).toBeTruthy()
    expect(within(nw).getByText(`.${cents}`)).toBeTruthy()
  })

  it('switches a chart to its table', async () => {
    renderApp('/')
    const nw = await screen.findByRole('region', { name: 'Net worth' })
    fireEvent.click(within(nw).getByRole('button', { name: 'Table' }))
    expect(within(nw).getByRole('table')).toBeTruthy()
    expect(within(nw).getAllByRole('row').length).toBeGreaterThan(200) // a year of weekdays
  })

  it('shows what needs you, most serious first', async () => {
    renderApp('/')
    const items = within(await screen.findByRole('region', { name: 'Needs you' })).getAllByRole('listitem')
    expect(items[0].textContent).toContain('MSFT has no resting stop')
    expect(items[0].textContent).toContain('Serious')
  })

  it('lists every book with its real/paper badge', async () => {
    renderApp('/')
    await screen.findByRole('region', { name: 'Books' })
    const rows = within(panel('Books')).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(homeFixture.books.length)
    expect(rows[0].textContent).toContain('REAL')
    expect(within(panel('Books')).getByText('Below band')).toBeTruthy()
  })

  it('puts the now line between done and due runs', async () => {
    renderApp('/')
    const today = await screen.findByRole('region', { name: 'Today' })
    const labels = within(today).getAllByRole('listitem').map((li) => li.getAttribute('aria-label') ?? li.textContent)
    const nowAt = labels.findIndex((l) => l?.startsWith('Now'))
    expect(labels[nowAt - 1]).toContain('ETF close entries')
    expect(labels[nowAt + 1]).toContain('Nightly suite')
  })

  it('caps the positions table and links to the rest', async () => {
    renderApp('/')
    const positions = await screen.findByRole('region', { name: 'Open positions' })
    expect(within(positions).getAllByRole('row')).toHaveLength(6) // header + 5
    expect(within(positions).getByText(`${homeFixture.positions.length - 5} more in Books`)).toBeTruthy()
  })

  it('handles a person with no data yet', async () => {
    const empty: HomeView = {
      ...homeFixture, allocation: [], accounts: [], attention: [], books: [], today: [], positions: [],
      comparison: { ...homeFixture.comparison, lines: [], dates: [], gap_pts: null, shallower: null },
      net_worth: { ...homeFixture.net_worth, total: 0, points: [] },
      summary: { day_change: 0, gap_pts: null, needs_you: 0 },
    }
    renderApp('/', { home: empty })
    expect(await screen.findByText('Nothing needs you right now.')).toBeTruthy()
    expect(screen.getByText('No open positions.')).toBeTruthy()
    expect(screen.getByText(/No history yet/)).toBeTruthy()
  })
})

describe('words from the data', () => {
  it('writes the summary sentence', () => {
    const base = homeFixture
    expect(summaryParts(base).needs).toBe('2 items need you.')
    const behind = { ...base, summary: { ...base.summary, gap_pts: -1.26, needs_you: 1 } }
    expect(summaryParts(behind)).toEqual({
      trading: 'Trading is behind your index money by 1.3 pts this year.', needs: 'One item needs you.',
    })
    expect(summaryParts({ ...base, summary: { ...base.summary, gap_pts: null, needs_you: 0 } }))
      .toEqual({ trading: null, needs: 'Nothing needs you.' })
  })

  it('writes the verdict with its sample-size caveat', () => {
    const v = verdict(homeFixture.comparison)
    expect(v?.headline).toMatch(/^Trading is ahead by 2\.9 pts this year, with a shallower worst drop/)
    expect(v?.caveat).toBe('34 real trades so far — early evidence. The strategy is reviewed at 50.')
    expect(verdict({ ...homeFixture.comparison, gap_pts: null })).toBeNull()
  })
})
````


- [ ] **Step 2: Run them and watch them fail**

Run (in `web/`): `npx vitest run src/charts src/pages`
Expected: fails to resolve `./geometry` and `./ComparisonPanel`.

- [ ] **Step 3: Implement the chart kit**

`web/src/charts/geometry.ts`:

````ts
// Pure chart math, tested without a DOM.
import type { ValuePoint } from '../lib/api'

export type Range = '1M' | '3M' | 'YTD' | '1Y'
export const RANGES: readonly Range[] = ['1M', '3M', 'YTD', '1Y']

/** Points inside the range, counted back from the last point's date. */
export function windowPoints(points: ValuePoint[], range: Range): ValuePoint[] {
  if (points.length === 0) return points
  const last = new Date(`${points[points.length - 1].date}T12:00:00Z`)
  const start = new Date(last)
  if (range === '1M') start.setUTCMonth(start.getUTCMonth() - 1)
  if (range === '3M') start.setUTCMonth(start.getUTCMonth() - 3)
  if (range === '1Y') start.setUTCFullYear(start.getUTCFullYear() - 1)
  if (range === 'YTD') start.setUTCMonth(0, 1)
  const from = start.toISOString().slice(0, 10)
  const inside = points.filter((p) => p.date >= from)
  return inside.length >= 2 ? inside : points.slice(-2)
}

/** The "starting value + deposits" line: what the account would hold if the market had not moved. */
export function baseline(points: ValuePoint[]): number[] {
  const out: number[] = []
  points.forEach((p, i) => out.push(i === 0 ? p.value : out[i - 1] + p.net_flow))
  return out
}

/** Index of the x closest to `x` (xs ascending). */
export function nearestIndex(xs: number[], x: number): number {
  if (xs.length === 0) return -1
  let lo = 0
  let hi = xs.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (xs[mid] <= x) lo = mid
    else hi = mid
  }
  return Math.abs(xs[lo] - x) <= Math.abs(xs[hi] - x) ? lo : hi
}

/** About `count` evenly spaced indices across n points, always including the first. */
export function tickIndices(n: number, count: number): number[] {
  if (n <= 0) return []
  if (n <= count) return Array.from({ length: n }, (_, i) => i)
  const step = (n - 1) / (count - 1)
  return Array.from({ length: count }, (_, i) => Math.round(i * step))
}
````

`web/src/charts/LineChart.tsx`:

````tsx
// One line chart for the whole app: hairline grid, right-hand value axis, crosshair tooltip on hover or keys.
import { max, min } from 'd3-array'
import { scaleLinear } from 'd3-scale'
import { area, curveLinear, curveStepAfter, line } from 'd3-shape'
import { type KeyboardEvent, type PointerEvent, useLayoutEffect, useRef, useState } from 'react'
import { nearestIndex, tickIndices } from './geometry'

export interface ChartSeries {
  key: string
  label: string
  values: (number | null)[]
  color: string // a CSS colour token, e.g. 'var(--s2)'
  style: 'solid' | 'dashed' | 'dotted' // real · paper · expected/benchmark
  area?: boolean
  step?: boolean
}

interface Props {
  dates: string[]
  series: ChartSeries[]
  height: number
  ariaLabel: string
  yFormat: (value: number) => string
  valueFormat: (value: number) => string
  xLabel: (iso: string) => string
  tipTitle: (iso: string) => string
  zeroLine?: boolean
  compact?: boolean
}

const DASH = { solid: undefined, dashed: '5 3.5', dotted: '1.5 3.5' } as const

function useWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(fallback)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setWidth(el.clientWidth || fallback)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [fallback])
  return [ref, width] as const
}

export function LineChart(props: Props) {
  const { dates, series, height, compact = false } = props
  const [wrapRef, width] = useWidth<HTMLDivElement>(640)
  const [hover, setHover] = useState<number | null>(null)
  const axisW = compact ? 0 : 56
  const bottom = compact ? 4 : 24
  const plotW = Math.max(40, width - axisW)
  const all = series.flatMap((s) => s.values).filter((v): v is number => v != null)
  const y = scaleLinear()
    .domain([min(all) ?? 0, max(all) ?? 1])
    .nice(4)
    .range([height - bottom, 8])
  const x = scaleLinear().domain([0, Math.max(1, dates.length - 1)]).range([0, plotW])
  const xs = dates.map((_, i) => x(i))
  const yTicks = compact ? [] : y.ticks(4)
  const xTicks = compact ? [] : tickIndices(dates.length, width < 480 ? 4 : 6)

  const pathOf = (s: ChartSeries) =>
    line<number | null>()
      .defined((v) => v != null)
      .x((_, i) => x(i))
      .y((v) => y(v as number))
      .curve(s.step ? curveStepAfter : curveLinear)(s.values) ?? ''
  const areaOf = (s: ChartSeries) =>
    area<number | null>()
      .defined((v) => v != null)
      .x((_, i) => x(i))
      .y0(height - bottom)
      .y1((v) => y(v as number))(s.values) ?? ''

  const onPointer = (event: PointerEvent<SVGSVGElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    setHover(nearestIndex(xs, event.clientX - box.left))
  }
  const onKey = (event: KeyboardEvent<SVGSVGElement>) => {
    const last = dates.length - 1
    const moves: Record<string, number> = {
      ArrowLeft: Math.max(0, (hover ?? last) - 1),
      ArrowRight: Math.min(last, (hover ?? last - 1) + 1),
      Home: 0,
      End: last,
    }
    if (event.key in moves) {
      event.preventDefault()
      setHover(moves[event.key])
    } else if (event.key === 'Escape') setHover(null)
  }

  const tipLeft = hover == null ? 0 : xs[hover] + 12 + 190 > plotW ? xs[hover] - 202 : xs[hover] + 12

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <svg width={width} height={height} role="img" aria-label={props.ariaLabel} tabIndex={0}
        style={{ display: 'block', overflow: 'visible', touchAction: 'pan-y' }}
        onPointerMove={onPointer} onPointerLeave={() => setHover(null)} onKeyDown={onKey} onBlur={() => setHover(null)}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={0} x2={plotW} y1={y(t)} y2={y(t)}
              stroke={props.zeroLine && t === 0 ? 'var(--line2)' : 'var(--line)'} />
            <text x={plotW + 10} y={y(t) + 4} fill="var(--ink3)" style={{ font: '11px var(--k-mono)' }}>
              {props.yFormat(t)}
            </text>
          </g>
        ))}
        {xTicks.map((i) => (
          <text key={i} x={xs[i]} y={height - 6} fill="var(--ink3)" style={{ font: '11px var(--k-sans)' }}
            textAnchor={i === 0 ? 'start' : i === dates.length - 1 ? 'end' : 'middle'}>
            {props.xLabel(dates[i])}
          </text>
        ))}
        {series.filter((s) => s.area).map((s) => (
          <path key={`${s.key}-area`} d={areaOf(s)} fill={s.color} fillOpacity={0.06} />
        ))}
        {series.map((s) => (
          <path key={s.key} d={pathOf(s)} fill="none" stroke={s.color} strokeWidth={s.style === 'dotted' ? 1.5 : 2}
            strokeDasharray={DASH[s.style]} strokeLinecap="round" strokeLinejoin="round" />
        ))}
        {hover == null && series.filter((s) => s.style === 'solid').map((s) => {
          const lastI = s.values.length - 1
          const v = s.values[lastI]
          return v == null ? null : (
            <circle key={`${s.key}-end`} cx={xs[lastI]} cy={y(v)} r={4} fill={s.color} stroke="var(--panel)" strokeWidth={2} />
          )
        })}
        {hover != null && (
          <g>
            <line x1={xs[hover]} x2={xs[hover]} y1={8} y2={height - bottom} stroke="var(--line2)" />
            {series.map((s) => {
              const v = s.values[hover]
              return v == null ? null : (
                <circle key={`${s.key}-hover`} cx={xs[hover]} cy={y(v)} r={4} fill={s.color} stroke="var(--panel)"
                  strokeWidth={2} />
              )
            })}
          </g>
        )}
      </svg>
      {hover != null && (
        <div className="tip" style={{ left: tipLeft, top: 4 }} role="status">
          <div style={{ color: 'var(--ink3)', fontSize: 11 }}>{props.tipTitle(dates[hover])}</div>
          {series.map((s) => (
            <div key={s.key} className="flex items-center justify-between gap-4" style={{ marginTop: 4 }}>
              <span style={{ color: 'var(--ink2)' }}>{s.label}</span>
              <span className="num" style={{ fontWeight: 500 }}>
                {s.values[hover] == null ? '—' : props.valueFormat(s.values[hover] as number)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/** The small legend key drawn beside a series name: the line in its real/paper/expected style. */
export function LineKey({ color, style }: { color: string; style: ChartSeries['style'] }) {
  return (
    <svg width="18" height="10" aria-hidden="true" style={{ flex: 'none' }}>
      <line x1="1" x2="17" y1="5" y2="5" stroke={color} strokeWidth={style === 'dotted' ? 1.5 : 2}
        strokeDasharray={style === 'dotted' ? '1.5 3' : style === 'dashed' ? '5 3' : undefined} strokeLinecap="round" />
    </svg>
  )
}
````


- [ ] **Step 4: Implement the panels and the full page**

`web/src/pages/home/NetWorthPanel.tsx`:

````tsx
import { useState } from 'react'
import { baseline, RANGES, type Range, windowPoints } from '../../charts/geometry'
import { LineChart, LineKey } from '../../charts/LineChart'
import { Delta, Panel, Seg } from '../../components/bits'
import type { NetWorth } from '../../lib/api'
import { compactMoney, monthLabel, money, pct, shortDate, signedMoney, splitCents } from '../../lib/format'

function Stat({ label, children, sub }: { label: string; children: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className="text-[13px] mt-1.5">{children}</div>
      {sub && <div className="text-xs text-ink3 mt-1">{sub}</div>}
    </div>
  )
}

export function NetWorthPanel({ nw }: { nw: NetWorth }) {
  const [range, setRange] = useState<Range>('1Y')
  const [view, setView] = useState<'Chart' | 'Table'>('Chart')
  const points = windowPoints(nw.points, range)
  const base = baseline(points)
  const growth = points.length ? points[points.length - 1].value - base[base.length - 1] : 0
  const [whole, cents] = splitCents(nw.total)
  return (
    <Panel id="net-worth" title="Net worth" span={8} height={372}
      actions={<>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ink1)" style="solid" />Net worth
        </span>
        <span className="hidden xl:inline-flex items-center gap-1.5 text-xs text-ink2">
          <LineKey color="var(--ref)" style="dotted" />Start + deposits
        </span>
        <Seg label="Range" options={RANGES} value={range} onChange={setRange} />
        <Seg label="View" options={['Chart', 'Table'] as const} value={view} onChange={setView} />
      </>}>
      <div className="flex flex-wrap items-end gap-x-9 gap-y-3 mt-3.5">
        <div className="text-5xl font-semibold tracking-[-0.035em] leading-none">
          {whole}<span className="text-ink3">.{cents}</span>
        </div>
        <div className="flex flex-wrap gap-x-7 gap-y-3 pb-1">
          <Stat label="Today" sub={nw.today.pct != null && pct(nw.today.pct, 2)}>
            <Delta value={nw.today.amount}>{signedMoney(nw.today.amount)}</Delta>
          </Stat>
          <Stat label="Month" sub={nw.month.pct != null && pct(nw.month.pct, 2)}>
            <Delta value={nw.month.amount}>{signedMoney(nw.month.amount)}</Delta>
          </Stat>
          <Stat label="Year" sub={<>incl. <span className="num">{money(nw.year_flows, false)}</span> deposited</>}>
            <Delta value={nw.year.amount}>{signedMoney(nw.year.amount)}</Delta>
          </Stat>
          <Stat label="Market" sub={`over ${range}`}>
            <Delta value={growth}>{signedMoney(growth, false)}</Delta>
          </Stat>
        </div>
      </div>
      <div className="mt-auto pt-3">
        {view === 'Chart' ? (
          <LineChart dates={points.map((p) => p.date)} height={196}
            ariaLabel="Net worth against your starting value plus deposits"
            series={[
              { key: 'nw', label: 'Net worth', values: points.map((p) => p.value), color: 'var(--ink1)', style: 'solid',
                area: true },
              { key: 'base', label: 'Start + deposits', values: base, color: 'var(--ref)', style: 'dotted', step: true },
            ]}
            yFormat={compactMoney} valueFormat={(v) => money(v, false)}
            xLabel={(d) => monthLabel(d, range === '1M' || range === '3M')} tipTitle={(d) => shortDate(d)} />
        ) : (
          <div className="overflow-y-auto" style={{ maxHeight: 196 }}>
            <table className="tbl">
              <thead><tr><th>Date</th><th className="r">Net worth</th><th className="r">Start + deposits</th></tr></thead>
              <tbody>
                {points.map((p, i) => (
                  <tr key={p.date}>
                    <td>{shortDate(p.date)}</td>
                    <td className="r num">{money(p.value)}</td>
                    <td className="r num">{money(base[i])}</td>
                  </tr>
                )).reverse()}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Panel>
  )
}
````

`web/src/pages/home/AllocationPanel.tsx`:

````tsx
import { Link } from '@tanstack/react-router'
import { Delta, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { AccountRow, Slice } from '../../lib/api'
import { money, pct } from '../../lib/format'

const COLOR: Record<string, string> = {
  long_term: 'var(--s1)', trading: 'var(--s2)', cash: 'var(--s3)', other: 'var(--ink3)',
}
const KIND: Record<string, string> = { long_term: 'Long-term', trading: 'Trading', cash: 'Cash', other: 'Other' }

/** 100 cells, filled column by column, so the waffle reads like one proportional bar. */
export function Waffle({ slices }: { slices: Slice[] }) {
  const cells = slices.flatMap((s) => Array.from({ length: s.cells }, () => s.category))
  return (
    <div role="img" aria-label={slices.map((s) => `${s.label} ${s.share.toFixed(1)} percent`).join(', ')}
      style={{ display: 'grid', gridTemplateColumns: 'repeat(20, minmax(0, 1fr))',
        gridTemplateRows: 'repeat(5, auto)', gridAutoFlow: 'column', gap: 4 }}>
      {cells.map((category, i) => (
        <span key={i} style={{ aspectRatio: '1', borderRadius: 2, background: COLOR[category] }} />
      ))}
    </div>
  )
}

export function AllocationPanel({ slices, accounts }: { slices: Slice[]; accounts: AccountRow[] }) {
  return (
    <Panel id="allocation" title="Where it sits" span={4} height={372}
      actions={<Link to="/accounts" className="text-xs inline-flex items-center gap-1">
        {accounts.length} accounts<Icon name="chevron" size={13} />
      </Link>}>
      <div className="mt-4"><Waffle slices={slices} /></div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-3">
        {slices.map((s) => (
          <span key={s.category} className="inline-flex items-center gap-1.5 text-[11.5px] text-ink2 whitespace-nowrap">
            <span className="mark real" style={{ '--mc': COLOR[s.category], width: 10, height: 10 } as React.CSSProperties} />
            {s.label} <span className="num text-ink1">{s.share.toFixed(1)}%</span>
          </span>
        ))}
      </div>
      <div className="mt-3.5 overflow-y-auto">
        {accounts.map((a) => (
          <div key={a.id} className="flex items-center gap-2.5 h-[42px] border-t border-line">
            <span className="w-2 h-2 rounded-full flex-none" style={{ background: COLOR[a.category] }} />
            <span className="text-[13px] font-medium truncate">{a.name}</span>
            <span className="text-[11px] text-ink3 hidden sm:inline">{KIND[a.category]}</span>
            <div className="ml-auto text-right">
              <div className="num text-[13px]">{money(a.value)}</div>
              <div className="text-[11px]">
                {a.day_pct == null ? <span className="text-ink3">—</span> : <Delta value={a.day_pct}>{pct(a.day_pct, 2)}</Delta>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}
````

`web/src/pages/home/ComparisonPanel.tsx`:

````tsx
import { useState } from 'react'
import { type ChartSeries, LineChart, LineKey } from '../../charts/LineChart'
import { Panel, Seg } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { Comparison, Line } from '../../lib/api'
import { monthLabel, pct, shortDate } from '../../lib/format'

const STYLE: Record<Line['key'], Pick<ChartSeries, 'color' | 'style'>> = {
  trading: { color: 'var(--s2)', style: 'solid' },
  long_term: { color: 'var(--s1)', style: 'solid' },
  benchmark: { color: 'var(--ref)', style: 'dotted' },
}

export function verdict(c: Comparison): { headline: string; caveat: string } | null {
  if (c.gap_pts == null) return null
  const period = c.window === 'ytd' ? 'this year' : 'over the past 12 months'
  const gap = Math.abs(c.gap_pts).toFixed(1)
  const trading = c.lines.find((l) => l.key === 'trading')
  const longTerm = c.lines.find((l) => l.key === 'long_term')
  const drops = trading && longTerm ? ` (${pct(trading.max_drop_pct)} vs ${pct(longTerm.max_drop_pct)})` : ''
  const headline = Math.abs(c.gap_pts) < 0.05
    ? `Trading is level with your index money ${period}.`
    : `Trading is ${c.gap_pts > 0 ? 'ahead' : 'behind'} by ${gap} pts ${period}, with a ${c.shallower ? 'shallower' : 'deeper'} worst drop${drops}.`
  const early = c.review_at != null && c.real_trades < c.review_at
  const caveat = early
    ? `${c.real_trades} real trades so far — early evidence. The strategy is reviewed at ${c.review_at}.`
    : `${c.real_trades} real trades so far.`
  return { headline, caveat }
}

export function ComparisonPanel({ c }: { c: Comparison }) {
  const [view, setView] = useState<'Chart' | 'Table'>('Chart')
  const v = verdict(c)
  const series: ChartSeries[] = c.lines.map((l) => ({ key: l.key, label: l.label, values: l.values, ...STYLE[l.key] }))
  return (
    <Panel id="comparison" title="Trading vs your index money" span={7} height={372}
      subtitle={`${c.window === 'ytd' ? 'Year to date' : 'Past 12 months'} · real money only · all start at 0%`}
      actions={<Seg label="View" options={['Chart', 'Table'] as const} value={view} onChange={setView} />}>
      {c.lines.length === 0 ? (
        <p className="text-ink3 mt-6">No history yet. The comparison appears once your accounts have a few days of data.</p>
      ) : (
        <div className="flex flex-col sm:flex-row gap-4 sm:gap-6 mt-3.5 min-h-0">
          <div className="flex-1 min-w-0">
            {view === 'Chart' ? (
              <LineChart dates={c.dates} series={series} height={190} zeroLine
                ariaLabel="Return since the start of the window: trading, long-term and the benchmark"
                yFormat={(n) => pct(n, 0)} valueFormat={(n) => pct(n)} xLabel={(d) => monthLabel(d)}
                tipTitle={(d) => shortDate(d)} />
            ) : (
              <table className="tbl">
                <thead><tr><th>Line</th><th className="r">Return</th><th className="r">Worst drop</th></tr></thead>
                <tbody>
                  {c.lines.map((l) => (
                    <tr key={l.key}><td>{l.label}</td><td className="r num">{pct(l.return_pct)}</td>
                      <td className="r num">{pct(l.max_drop_pct)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="grid grid-cols-3 gap-2.5 sm:flex sm:flex-col sm:w-[150px] flex-none">
            {c.lines.map((l) => (
              <div key={l.key}>
                <div className="flex items-center gap-2 text-xs text-ink2">
                  <LineKey {...STYLE[l.key]} />{l.label}
                </div>
                <div className="num text-xl font-medium mt-1">{pct(l.return_pct)}</div>
                <div className="num text-[11px] text-ink3">max drop {pct(l.max_drop_pct)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {v && (
        <div className="mt-auto flex gap-3 items-start rounded-lg border border-line bg-panel2 px-3.5 py-3">
          <Icon name="scale" size={18} style={{ color: 'var(--ink2)', marginTop: 1 }} />
          <div>
            <div className="text-[13px] font-medium">{v.headline}</div>
            <div className="text-xs text-ink3 mt-0.5">{v.caveat}</div>
          </div>
        </div>
      )}
    </Panel>
  )
}
````

`web/src/pages/home/AttentionPanel.tsx`:

````tsx
import { Link } from '@tanstack/react-router'
import { Panel } from '../../components/bits'
import { Icon, type IconName } from '../../components/Icon'
import type { Attention, Level } from '../../lib/api'

const LOOK: Record<Level, { icon: IconName; color: string; word: string }> = {
  serious: { icon: 'shield', color: 'var(--serious)', word: 'Serious' },
  warning: { icon: 'clock', color: 'var(--warn)', word: 'Warning' },
  note: { icon: 'info', color: 'var(--ink3)', word: 'Note' },
}
const SHOWN = 3

export function AttentionPanel({ items }: { items: Attention[] }) {
  const counts = (['serious', 'warning', 'note'] as const)
    .map((level) => [level, items.filter((i) => i.level === level).length] as const)
    .filter(([, n]) => n > 0)
    .map(([level, n]) => `${n} ${level}`)
  return (
    <Panel id="attention" title="Needs you" span={5} height={372}
      actions={counts.length > 0 && <span className="chip">{counts.join(' · ')}</span>}>
      {items.length === 0 ? (
        <div className="flex items-center gap-2 mt-6 text-ink2">
          <Icon name="checkCircle" size={18} style={{ color: 'var(--good)' }} />Nothing needs you right now.
        </div>
      ) : (
        <ul className="mt-3">
          {items.slice(0, SHOWN).map((item, i) => {
            const look = LOOK[item.level]
            return (
              <li key={i} className="flex gap-3 py-3.5 border-t border-line">
                <span className="w-8 h-8 flex-none rounded-lg bg-panel2 border border-line flex items-center justify-center"
                  style={{ color: look.color }}>
                  <Icon name={look.icon} size={16} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="label" style={{ color: look.color }}>{look.word}</div>
                  <div className="text-sm font-medium mt-0.5">{item.title}</div>
                  {item.detail && <div className="text-xs text-ink3 mt-0.5">{item.detail}</div>}
                </div>
                {item.link && (
                  <Link to={item.link} className="self-center inline-flex items-center gap-1 text-xs whitespace-nowrap"
                    style={{ color: 'var(--acc-ink)' }}>
                    Open<Icon name="arrow" size={13} />
                  </Link>
                )}
              </li>
            )
          })}
        </ul>
      )}
      {items.length > SHOWN && (
        <Link to="/activity" className="mt-auto text-xs" style={{ color: 'var(--acc-ink)' }}>
          {items.length - SHOWN} more
        </Link>
      )}
    </Panel>
  )
}
````

`web/src/pages/home/BooksPanel.tsx`:

````tsx
import { BookMark, Delta, Missing, MoneyBadge, Panel } from '../../components/bits'
import { Icon } from '../../components/Icon'
import type { BookRow } from '../../lib/api'
import { money, pct, shortDate, signedMoney, sinceLabel, timeHM } from '../../lib/format'

/** The per-trade result against its expected 95% band: dotted band, zero tick, a dot for the actual. */
export function BandBar({ lo, hi, actual }: { lo: number; hi: number; actual: number }) {
  const W = 110
  const low = Math.min(lo, actual, 0)
  const high = Math.max(hi, actual, 0)
  const pad = (high - low) * 0.15 || 1
  const x = (v: number) => ((v - (low - pad)) / (high + pad - (low - pad))) * W
  return (
    <svg width={W} height={14} aria-hidden="true" style={{ display: 'block', overflow: 'visible' }}>
      <line x1={0} x2={W} y1={7} y2={7} stroke="var(--line2)" />
      <rect x={x(lo)} y={2} width={Math.max(2, x(hi) - x(lo))} height={10} rx={3} fill="var(--ink1)" fillOpacity={0.06}
        stroke="var(--ref)" strokeDasharray="1.5 2.5" />
      <line x1={x(0)} x2={x(0)} y1={0} y2={14} stroke="var(--ink3)" />
      <circle cx={x(actual)} cy={7} r={4} fill="var(--ink1)" stroke="var(--panel)" strokeWidth={2} />
    </svg>
  )
}

function Slots({ used, total, money: kind }: { used: number; total: number; money: BookRow['money'] }) {
  return (
    <div className="flex gap-[3px]" role="img" aria-label={`${used} of ${total} slots in use`}>
      {Array.from({ length: total }, (_, i) => i < used
        ? <BookMark key={i} kind={kind} size={10} />
        : <span key={i} className="w-2.5 h-2.5 rounded-sm" style={{ boxShadow: 'inset 0 0 0 1px var(--line2)' }} />)}
    </div>
  )
}

const VERDICT: Record<BookRow['verdict'], string> = {
  in_band: 'In band', below: 'Below band', above: 'Above band', early: 'Too early', none: '—',
}

export function BooksPanel({ books, tz, now }: { books: BookRow[]; tz: string; now: string }) {
  return (
    <Panel id="books" title="Books" subtitle="Every strategy, real and paper, side by side" span={12}
      actions={<div className="hidden md:flex items-center gap-4 text-xs text-ink2">
        <span className="inline-flex items-center gap-1.5"><BookMark kind="real" />Real money</span>
        <span className="inline-flex items-center gap-1.5"><BookMark kind="paper" />Paper</span>
        <span className="inline-flex items-center gap-1.5"><BookMark kind="expected" />Expected range</span>
      </div>}>
      <div className="table-scroll mt-4">
        <table className="tbl" style={{ minWidth: 900 }}>
          <thead>
            <tr>
              <th>Book</th><th>Money</th><th className="r">Value</th><th className="r">Today</th>
              <th className="r">Since start</th><th style={{ paddingLeft: 28 }}>Per trade vs expected</th>
              <th>Slots</th><th>Status</th>
            </tr>
          </thead>
          <tbody>
            {books.map((b) => (
              <tr key={b.id}>
                <td>
                  <div className="flex items-center gap-3">
                    <BookMark kind={b.money} size={14} />
                    <div>
                      <div className="font-medium">{b.name}</div>
                      <div className="text-xs text-ink3 mt-0.5">{b.trades} trades · since {sinceLabel(b.started, now)}</div>
                    </div>
                  </div>
                </td>
                <td><MoneyBadge money={b.money} /></td>
                <td className="r num">{money(b.value)}</td>
                <td className="r">{b.day_change == null ? <Missing /> : <Delta value={b.day_change}>{signedMoney(b.day_change)}</Delta>}</td>
                <td className="r">{b.since_pct == null ? <Missing /> : <Delta value={b.since_pct}>{pct(b.since_pct)}</Delta>}</td>
                <td style={{ paddingLeft: 28 }}>
                  {b.band_lo != null && b.band_hi != null && b.per_trade_pct != null && (
                    <BandBar lo={b.band_lo} hi={b.band_hi} actual={b.per_trade_pct} />
                  )}
                  <div className="text-[11px] mt-1.5 flex items-center gap-1.5 whitespace-nowrap"
                    style={{ color: b.verdict === 'below' ? 'var(--ink1)' : 'var(--ink3)' }}>
                    {b.verdict === 'below' && <Icon name="alert" size={12} style={{ color: 'var(--warn)' }} />}
                    {VERDICT[b.verdict]}
                    {b.verdict === 'early' && ` · ${b.trades} trades`}
                    {b.per_trade_pct != null && b.verdict !== 'early' && b.verdict !== 'none' &&
                      <span className="num"> · {pct(b.per_trade_pct, 2)}</span>}
                  </div>
                </td>
                <td>
                  {b.slots_total ? <><Slots used={b.slots_used} total={b.slots_total} money={b.money} />
                    <div className="num text-[11px] text-ink3 mt-1.5">{b.slots_used} of {b.slots_total}</div></> : <Missing />}
                </td>
                <td>
                  <div className="flex items-center gap-2 text-[13px] capitalize">
                    <span className="w-2 h-2 rounded-full" style={b.status === 'running'
                      ? { background: 'var(--good)' } : { boxShadow: 'inset 0 0 0 1.5px var(--ink3)' }} />
                    {b.status}
                  </div>
                  <div className="num text-[11px] text-ink3 mt-1">
                    {b.next_run ? `${shortDate(b.next_run, tz).slice(0, 3)} ${timeHM(b.next_run, tz)}` : '—'}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
````

`web/src/pages/home/TodayAndPositions.tsx`:

````tsx
import { Link } from '@tanstack/react-router'
import { Fragment } from 'react'
import { BookMark, Delta, Panel } from '../../components/bits'
import { Icon, type IconName } from '../../components/Icon'
import type { PositionRow, TodayRun } from '../../lib/api'
import { num, shortDate, signedMoney, timeHM } from '../../lib/format'

const RUN_ICON: Record<TodayRun['status'], { name: IconName; color: string }> = {
  done: { name: 'checkCircle', color: 'var(--good)' },
  due: { name: 'circle', color: 'var(--ink3)' },
  late: { name: 'clock', color: 'var(--warn)' },
  failed: { name: 'alert', color: 'var(--serious)' },
  paused: { name: 'circle', color: 'var(--ink3)' },
}

export function TodayPanel({ runs, now, tz }: { runs: TodayRun[]; now: string; tz: string }) {
  const nowMs = new Date(now).getTime() // compare instants, never ISO strings with different offsets
  const nowIndex = runs.findIndex((r) => new Date(r.time).getTime() > nowMs)
  const nowLine = (
    <li className="flex items-center gap-2.5 h-[26px]" aria-label={`Now, ${timeHM(now, tz)}`}>
      <span className="num w-11 text-[11px] font-semibold" style={{ color: 'var(--acc-ink)' }}>{timeHM(now, tz)}</span>
      <span className="flex-1 h-px" style={{ background: 'var(--acc)' }} />
      <span className="label" style={{ color: 'var(--acc-ink)' }}>Now</span>
    </li>
  )
  return (
    <Panel id="today" title="Today" span={5} height={372}
      actions={<span className="num text-xs text-ink3">{shortDate(now, tz)}</span>}>
      {runs.length === 0 ? (
        <p className="text-ink3 mt-6">Nothing is scheduled today.</p>
      ) : (
        <ul className="mt-2.5">
          {runs.map((run, i) => {
            const icon = RUN_ICON[run.status]
            return (
              <Fragment key={`${run.time}-${run.label}`}>
                {i === nowIndex && nowLine}
                <li className="flex items-center gap-2.5 h-10">
                  <span className="num w-11 text-xs text-ink2">{timeHM(run.time, tz)}</span>
                  <Icon name={icon.name} size={16} style={{ color: icon.color }} />
                  <span className="sr-only">{run.status}</span>
                  <div className="min-w-0">
                    <div className="text-[13px] font-medium truncate"
                      style={{ color: run.status === 'done' ? 'var(--ink2)' : 'var(--ink1)' }}>{run.label}</div>
                    <div className="text-[11px] text-ink3 truncate">{run.detail}</div>
                  </div>
                </li>
              </Fragment>
            )
          })}
          {nowIndex === -1 && nowLine}
        </ul>
      )}
    </Panel>
  )
}

const SHOWN = 5

export function PositionsPanel({ positions }: { positions: PositionRow[] }) {
  const real = positions.filter((p) => p.money === 'real').length
  return (
    <Panel id="positions" title="Open positions" span={7} height={372}
      actions={<span className="text-xs text-ink3">{positions.length} open · {real} real, {positions.length - real} paper</span>}>
      {positions.length === 0 ? (
        <p className="text-ink3 mt-6">No open positions.</p>
      ) : (
        <div className="table-scroll mt-3.5">
          <table className="tbl" style={{ minWidth: 560, '--row': '50px' } as React.CSSProperties}>
            <thead>
              <tr><th>Symbol</th><th className="r">Qty</th><th className="r">Entry</th><th className="r">Last</th>
                <th className="r">Stop</th><th style={{ paddingLeft: 16 }}>Room to stop</th><th className="r">P/L</th></tr>
            </thead>
            <tbody>
              {positions.slice(0, SHOWN).map((p) => (
                <tr key={`${p.book_id}-${p.symbol}`}>
                  <td>
                    <div className="flex items-center gap-2.5">
                      <BookMark kind={p.money} />
                      <span className="num font-semibold">{p.symbol}</span>
                      <span className="sr-only">{p.money} · {p.book}</span>
                    </div>
                  </td>
                  <td className="r num">{num(p.quantity, 0)}</td>
                  <td className="r num">{num(p.entry_price)}</td>
                  <td className="r num">{num(p.last_price)}</td>
                  <td className="r num">{p.stop_price == null ? <span className="text-ink3">—</span> : num(p.stop_price)}</td>
                  <td style={{ paddingLeft: 16 }}>
                    {p.room_pct != null ? (
                      <div className="flex items-center gap-2">
                        <span className="relative w-14 h-1.5 rounded-full overflow-hidden bg-panel2"
                          style={{ boxShadow: 'inset 0 0 0 1px var(--line)' }}>
                          <span className="absolute inset-y-0 left-0" style={{
                            width: `${Math.min(100, (p.room_pct / 12) * 100)}%`,
                            background: p.room_pct < 8 ? 'var(--warn)' : 'var(--ink3)',
                          }} />
                        </span>
                        <span className="num text-xs">{p.room_pct.toFixed(1)}%</span>
                      </div>
                    ) : p.money === 'real' ? (
                      <span className="flex items-center gap-1.5 text-xs">
                        <Icon name="shield" size={14} style={{ color: 'var(--serious)' }} />No stop
                      </span>
                    ) : (
                      <span className="text-xs text-ink3">{p.note || '—'}</span>
                    )}
                  </td>
                  <td className="r"><Delta value={p.pnl}>{signedMoney(p.pnl)}</Delta></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {positions.length > SHOWN && (
        <Link to="/books" className="mt-auto text-xs pt-2" style={{ color: 'var(--acc-ink)' }}>
          {positions.length - SHOWN} more in Books
        </Link>
      )}
    </Panel>
  )
}
````

`web/src/pages/home/Home.tsx`:

````tsx
import { Delta } from '../../components/bits'
import { type HomeView, useHome, useShell } from '../../lib/api'
import { signedMoney } from '../../lib/format'
import { AllocationPanel } from './AllocationPanel'
import { AttentionPanel } from './AttentionPanel'
import { BooksPanel } from './BooksPanel'
import { ComparisonPanel } from './ComparisonPanel'
import { NetWorthPanel } from './NetWorthPanel'
import { PositionsPanel, TodayPanel } from './TodayAndPositions'

/** The sentence under the page title, written from the data. */
export function summaryParts(h: HomeView): { trading: string | null; needs: string } {
  const gap = h.summary.gap_pts
  const period = h.comparison.window === 'ytd' ? 'this year' : 'over the past 12 months'
  const trading = gap == null ? null : Math.abs(gap) < 0.05
    ? `Trading is level with your index money ${period}.`
    : `Trading is ${gap > 0 ? 'ahead of' : 'behind'} your index money by ${Math.abs(gap).toFixed(1)} pts ${period}.`
  const n = h.summary.needs_you
  const needs = n === 0 ? 'Nothing needs you.' : n === 1 ? 'One item needs you.' : `${n} items need you.`
  return { trading, needs }
}

export function Home() {
  const home = useHome()
  const shell = useShell()
  if (home.isPending) {
    return <p className="text-ink3" role="status">Loading your money…</p>
  }
  if (home.isError) {
    return <div role="alert" className="panel">Home couldn&rsquo;t load: {home.error.message}</div>
  }
  const h = home.data
  const tz = shell.data?.app.timezone ?? 'UTC'
  const { trading, needs } = summaryParts(h)
  return (
    <>
      <header className="mb-5">
        <h1 className="text-[28px] font-semibold tracking-[-0.025em]">Home</h1>
        <p className="text-ink2 mt-1.5">
          All your money is <Delta value={h.summary.day_change}>{signedMoney(h.summary.day_change)}</Delta> today.{' '}
          {trading && <>{trading} </>}{needs}
        </p>
      </header>
      <div className="grid12">
        <NetWorthPanel nw={h.net_worth} />
        <AllocationPanel slices={h.allocation} accounts={h.accounts} />
        <ComparisonPanel c={h.comparison} />
        <AttentionPanel items={h.attention} />
        <BooksPanel books={h.books} tz={tz} now={h.as_of} />
        <TodayPanel runs={h.today} now={h.as_of} tz={tz} />
        <PositionsPanel positions={h.positions} />
      </div>
    </>
  )
}
````


- [ ] **Step 5: Run everything and watch it pass**

Run (in `web/`): `npx vitest run && npx tsc --noEmit && npm run build`
Expected: `Test Files 7 passed`, `Tests 35 passed`; tsc clean; the CSS bundle is about 18 KB and the JS about 392 KB (126 KB gzipped).

- [ ] **Step 6: Commit**

```bash
git add web/src
git commit -m "feat(home): net worth, allocation, trading vs index, needs you, books, today and positions"
```

---

### Task 11: CI, docs, and the screenshot pass

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md` (status and "Run it"), `AGENTS.md` (status, run and test, the where-things-are rows), `docs/specs/2026-09-25-kestrel-design.md` (§11: Phase 2 → `done`)

- [ ] **Step 1: Add CI**

`.github/workflows/ci.yml`:

````yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  python:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest
  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: web/package-lock.json
      - run: npm ci
      - run: npm test
      - run: npm run build
````


- [ ] **Step 2: Update the docs**

The full new `README.md` and `AGENTS.md` are below. In the spec's §11 table, change the Phase 2 row's state from `next` to `done`, and Phase 3's from empty to `next`.

`README.md`:

````markdown
# kestrel

**One calm, read-only home for all your money.** Your long-term accounts, your trading account and every paper
book appear side by side. Each strategy gets a page that shows how it trades and whether it's behaving the way its
backtest said it would.

> **Status: Phase 2 of 5 — the skeleton runs.** Home works end to end on demo data; Accounts, Books, Strategies,
> Backtests, Activity and Settings arrive in later phases. See the [design spec](docs/specs/2026-09-25-kestrel-design.md).

## What it shows

- **Home:**
  - net worth, with how much of the growth was your deposits versus the market,
  - where your money sits,
  - **your trading vs your index money**, meaning whether the active side is earning its keep net of drawdown,
  - what needs you,
  - every book at a glance,
  - today's runs,
  - open positions with their room to stop.
- **Strategies:**
  - the rule drawn as four steps,
  - real trades against the backtest's spread of outcomes,
  - a running average inside the expected funnel,
  - how much of the money is working,
  - trade anatomy,
  - return against worst drop,
  - month by month.
- **Books, Accounts, Backtests, Activity and Settings** are built from the same components.

Reference mockups, drawn with fictional demo data; clone and open them in a browser:
[Home](docs/design/mockups/home.html) ·
[Home, light](docs/design/mockups/home-light.html) ·
[Strategy](docs/design/mockups/strategy.html) ·
[Phone](docs/design/mockups/phone.html)

## Principles

- **Read-only.** kestrel never places, changes or cancels an order. Your trading desk does that.
- **Personal, not published.**
  - It greets you by name and shows your accounts, but all of that comes from a local, gitignored `profile.toml` and
    your own data sources.
  - Nothing personal lives in the repo.
  - Someone else can clone it and point it at their own keys.
- **Made to last.**
  - A restrained, token-driven design ([Graphite](docs/design-system.md)): graphite neutrals, one accent, and the data
    as the only colour.
  - Real money is solid, paper is hatched, and expected is dotted, everywhere.

## How it fits

| Repo | Job |
|---|---|
| [financial-data-collector](https://github.com/Dimas-100/financial-data-collector) | collects accounts, holdings and prices |
| [trading-rails](https://github.com/Dimas-100/trading-rails) | trades safely: paper broker, safety gate, backtests |
| **kestrel** | shows it all; reads the two above, or any source that speaks its data contract |

## Run it

Needs Python 3.11+ and Node 24+.

```bash
git clone <this repo> && cd kestrel
python -m venv .venv && .venv/bin/pip install -e .      # Windows: .venv\Scripts\pip
(cd web && npm ci && npm run build)
.venv/bin/kestrel serve                                  # opens http://127.0.0.1:8030 with demo data
```

Make it yours: copy `profile.example.toml` to `profile.toml` (gitignored) and set your name, look and sources.
`kestrel check` validates the profile and tries every source; `kestrel demo` prints the demo data as an example feed;
`kestrel schema` prints the [data contract](docs/data-contract.md).

## License

MIT, see [LICENSE](LICENSE).
````

`AGENTS.md`:

````markdown
# AGENTS.md

These instructions are for anyone working on this repo, whether you are a human contributor or using an AI coding
assistant (Claude Code, Codex, Cursor, Gemini CLI, Copilot, or any tool that reads this file). Nothing here is
specific to one assistant.

**What kestrel is:** a read-only, personal dashboard that brings all of someone's money into one place:
- long-term accounts,
- a trading account,
- every paper-trading book,

with pages that explain each strategy and whether it is behaving as expected. The design is in
`docs/specs/2026-09-25-kestrel-design.md`, and the look is in `docs/design-system.md`.

**Status:** Phase 2 of 5 — the skeleton: contract, profile, demo connector, read-only server, shell and Home.

## Hard invariants

1. **Read-only, always.**
   - Never add a route other than GET.
   - Never import or call anything that places, changes or cancels an order.
   - Never write to a data source.
   
   kestrel *shows* money; the user's own trading desk trades it. From Phase 2, a route-walk test and an import
   guard pin this. New checks may only add strictness. Asked to "just add a buy button", say no and point here.
2. **Nothing personal in git.**
   - Names, account numbers, balances, holdings and machine paths arrive only at runtime, through the gitignored
     `profile.toml` and the user's connectors.
   - Demo data is fictional ("Alex").
   - Never commit `profile.toml`, `.env*`, `data/`, keys, or symbols copied from a real book.
   
   `tests/test_hygiene.py` enforces the mechanical part (paths, private hosts, personal email addresses); the rest
   is on you.
3. **The design system is the source of truth for the look.**
   - Use the tokens in `docs/design-system.md` and never raw hex values in components.
   - Real money is solid, paper is hatched, and expected is dotted, everywhere.
   - Never encode meaning by colour alone.
   - Re-run the palette validator before changing any colour, and record the result in the design-system doc.
4. **Every chart has a table view, every page works by keyboard, and no panel overflows.** Check this with a
   screenshot pass at 1440 px and 390 px in both themes.

## Run and test

- **Python:** `pip install -e ".[dev]"` · `pytest` · `ruff check .` · `kestrel serve` (127.0.0.1:8030).
- **Web (in `web/`):** `npm ci` · `npm test` · `npm run build` (served by `kestrel serve` from `web/dist`).
  For live reload run `kestrel serve --no-open` and `npm run dev` side by side (Vite proxies `/api`).
- **Generated files** — the contract schema and the web test fixtures — are rebuilt with the commands a failing
  `tests/test_generated_files.py` prints.

## Where things are

| Path | What |
|---|---|
| `docs/specs/` | One design spec per phase or feature. The first is the overall design. |
| `docs/design-system.md` | Tokens, typography, layout, components, chart rules, copy rules |
| `docs/design/mockups/` | Reference mockups (fictional demo data) |
| `src/kestrel/` | Contract, profile, connectors, views, the read-only server, the CLI |
| `web/src/` | The app: `styles/tokens.css` (design tokens), `shell/`, `charts/`, `pages/` |
| `docs/data-contract.md` | The Snapshot format any source speaks; schema in `docs/contract/` |
| `tests/test_read_only_guard.py` · `tests/test_hygiene.py` | Never an order path · never private data in git |

## How work happens

Each phase goes spec → plan → build, in small commits. Docs change in the same commit as the behaviour they
describe.
````


- [ ] **Step 3: Run everything from a clean start**

```bash
.venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check .
(cd web && npm ci && npm test && npm run build)
```
Expected: 71 passed · ruff clean · 35 passed · `✓ built`.

- [ ] **Step 4: The screenshot pass (the check jsdom can't do)**

Run `.venv/Scripts/kestrel serve --no-open` and open `http://127.0.0.1:8030`. At 1440 × 1000, 1024, 768 and 390 × 844, in both themes (use the theme button, or `localStorage.setItem('kestrel.theme', 'light'|'dark')` and reload), paste this into the browser console:

```js
(() => {
  const over = [...document.querySelectorAll('section.panel')]
    .filter((s) => s.scrollHeight > s.clientHeight + 1).map((s) => s.getAttribute('aria-labelledby'))
  return { sidewaysScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth, over }
})()
```
Expected at every width and theme: `{ sidewaysScroll: 0, over: [] }`.

Then look at each screenshot:
- **Graphite dark:** it matches `docs/design/mockups/home.html`.
- **Light:** it matches `home-light.html`.
- **At 390 px:** the sidebar hides behind the menu button, the tab bar sits at the bottom, and tables scroll inside their panels.
- **Hover:** hovering the net-worth chart shows the crosshair tooltip. Tab to it and use ←/→.

- [ ] **Step 5: Commit, push, and watch CI**

```bash
git add .github/workflows/ci.yml README.md AGENTS.md docs/specs/2026-09-25-kestrel-design.md
git commit -m "ci: python 3.11/3.12 and node 24 jobs; docs: Phase 2 status and run instructions"
git push
gh run watch --exit-status
```
Expected: both CI jobs green.

---

## Done when

- `kestrel serve` shows Home on demo data in both themes, and every other nav item opens an honest "Phase N" page.
- 71 Python tests and 35 web tests pass locally and in CI; ruff and tsc are clean.
- The screenshot pass shows no overflow and no sideways scroll at 390 to 1440 px.
- No real account data, machine path or personal email is in the tree (`tests/test_hygiene.py`).
