"""financial-data-collector's SQLite warehouse, read-only: accounts, what they hold, their daily history with the
money moved in and out, and the benchmark's prices.

The warehouse is opened read-only twice over (mode=ro, then query_only) and closed straight after each read; reads
are cached until the file changes (see `FdcConnector._load`). Nothing here ever writes to it.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time as _time  # aliased: `time` below is datetime.time, used for the US close
import unicodedata
from bisect import bisect_left
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

from ..contract import Account, Benchmark, Category, Holding, Series, Snapshot, Source, ValuePoint
from ..profile import BenchmarkCfg
from .base import ConnectorError

TIMEOUT = 5.0  # seconds to wait for a warehouse another process is writing
MIN_VERSION = 6  # accounts.flows, credit_limit and rate_pct, and cash_balances.available, arrived in migration 6
REQUIRED = ("accounts", "transactions", "prices", "sync_runs", "holdings_daily", "cash_daily", "positions_latest",
            "account_values_daily")
CLOSE = time(16, 0, tzinfo=ZoneInfo("America/New_York"))  # a day's values are the US close
UPDATE = "update financial-data-collector and run `fdc sync`"

INSTITUTIONS = {"fidelity": "Fidelity", "webull": "Webull", "unknown": ""}
TYPES = {"roth_ira": "Roth IRA", "traditional_ira": "Traditional IRA", "brokerage": "Brokerage", "crypto": "Crypto",
         "401k": "401(k)", "403b": "403(b)", "457b": "457(b)", "ira": "IRA", "rollover_ira": "Rollover IRA",
         "sep_ira": "SEP IRA", "simple_ira": "SIMPLE IRA", "hsa": "HSA", "checking": "Checking", "savings": "Savings",
         "money_market": "Money market", "credit_card": "Credit card", "loan": "Loan", "mortgage": "Mortgage",
         "line_of_credit": "Line of credit"}
LONG_TERM = {"roth_ira", "traditional_ira", "ira", "rollover_ira", "sep_ira", "simple_ira", "401k", "403b", "457b",
             "hsa", "pension", "brokerage"}
CASH = {"checking", "savings", "cash", "money_market"}
DEBT = {"credit_card", "loan", "mortgage", "line_of_credit"}  # the collector stores what these owe below zero

# each account's value per day: its holdings plus its cash, the join portfolio_daily_full uses, kept per account
HISTORY = """
WITH h AS (SELECT as_of_date, account_id, SUM(market_value) AS holdings FROM holdings_daily GROUP BY 1, 2),
     c AS (SELECT as_of_date, account_id, amount AS cash FROM cash_daily),
     d AS (SELECT as_of_date, account_id FROM h UNION SELECT as_of_date, account_id FROM c)
SELECT d.account_id, d.as_of_date, COALESCE(h.holdings, 0), COALESCE(c.cash, 0)
FROM d
LEFT JOIN h ON h.as_of_date = d.as_of_date AND h.account_id = d.account_id
LEFT JOIN c ON c.as_of_date = d.as_of_date AND c.account_id = d.account_id
ORDER BY d.account_id, d.as_of_date
"""
FLOWS = """
SELECT account_id, trade_date, type, amount FROM transactions
WHERE type IN ('contribution', 'withdrawal', 'transfer') AND amount IS NOT NULL
"""


def slug(label: str) -> str:
    """A label as an id: "Alex Roth IRA" is alex-roth-ira. Accents fold to their letter first ("É" is e); a label
    with nothing left is "account"."""
    folded = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-") or "account"


def account_ids(labels: list[str]) -> list[str]:
    """Each label's slug, in order; a clash gets -2, -3 (the collector's own slug column isn't unique)."""
    taken: set[str] = set()
    ids = []
    for label in labels:
        base = candidate = slug(label)
        n = 2
        while candidate in taken:
            candidate, n = f"{base}-{n}", n + 1
        taken.add(candidate)
        ids.append(candidate)
    return ids


def _words(code: str) -> str:
    return code.replace("_", " ").strip().title()


def institution_text(code: str) -> str:
    return INSTITUTIONS.get(code, _words(code))


def type_text(code: str) -> str:
    return TYPES.get(code, _words(code))


def category_of(account_type: str) -> Category:
    if account_type in LONG_TERM:
        return "long_term"
    if account_type in CASH:
        return "cash"
    return "debt" if account_type in DEBT else "other"


def _close(day: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), CLOSE)


def _utc(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _flow(kind: str, amount: float) -> float:
    """A withdrawal is money out whatever its sign; a contribution or a transfer keeps its own (a negative
    contribution is a reversal)."""
    return -abs(amount) if kind == "withdrawal" else amount


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _day(text: str) -> str:
    """An ISO day as "24 Sep"."""
    day = date.fromisoformat(text)
    return f"{day.day} {day:%b}"


@contextmanager
def connect(path: Path, timeout: float = TIMEOUT) -> Iterator[sqlite3.Connection]:
    """The warehouse, read-only: opened with mode=ro, then query_only on top. Always closed."""
    if not path.is_file():
        raise ConnectorError(f"no warehouse at {path}")  # checked first, so SQLite never creates one
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=timeout)
    try:
        conn.execute("PRAGMA query_only = 1")
        yield conn
    finally:
        conn.close()


def check_schema(conn: sqlite3.Connection, path: Path) -> None:
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
    if "schema_version" not in names:
        raise ConnectorError(f"{path} is not a financial-data-collector warehouse (it has no schema_version table)")
    version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] or 0
    if version < MIN_VERSION:
        raise ConnectorError(f"this warehouse is at schema version {version} and kestrel needs {MIN_VERSION}: {UPDATE}")
    missing = [name for name in REQUIRED if name not in names]
    if missing:
        raise ConnectorError(f"this warehouse is missing {', '.join(missing)}: {UPDATE}")


def last_success(conn: sqlite3.Connection) -> datetime | None:
    """When the warehouse last finished a good `derive` step (the one that rebuilds the daily history), else any
    good step; None when nothing has ever gone right."""
    query = "SELECT MAX(finished_at) FROM sync_runs WHERE status = 'ok'"
    derived = conn.execute(query + " AND step = 'derive'").fetchone()[0]
    return _utc(derived or conn.execute(query).fetchone()[0])


def history(conn: sqlite3.Connection) -> dict[int, list[tuple[str, float, float]]]:
    """Per account (the warehouse's own id): (day, value, cash), days ascending."""
    out: dict[int, list[tuple[str, float, float]]] = defaultdict(list)
    for account, day, holdings, cash in conn.execute(HISTORY):
        out[account].append((day, holdings + cash, cash))
    return out


def _with_snapshot(points: list[tuple[str, float, float]],
                   snapped: tuple[str, float, float] | None) -> list[tuple[str, float, float]]:
    """The replayed history with the broker's latest snapshot laid over it, so an account's value and the last
    point of its history are one number: on the same day the snapshot's total replaces the replayed one, a newer
    snapshot is one more day, and an older one changes nothing."""
    if snapped is None or (points and snapped[0] < points[-1][0]):
        return points
    if points and snapped[0] == points[-1][0]:
        return [*points[:-1], snapped]
    return [*points, snapped]


def flows(conn: sqlite3.Connection, days: dict[int, list[str]]) -> dict[int, dict[str, float]]:
    """Per account, the money moved in or out, filed under a history day: a flow on a day without a point goes to
    the next one (a Saturday deposit is Monday's), and one after the last point is dropped."""
    out: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for account, when, kind, amount in conn.execute(FLOWS):
        known = days.get(account, [])
        i = bisect_left(known, when[:10])
        if i < len(known):
            out[account][known[i]] += _flow(kind, amount)
    return out


FileState = tuple[int, int] | None  # (st_mtime_ns, st_size); None when the file doesn't exist


def _file_state(path: Path) -> FileState:
    try:
        info = path.stat()
    except OSError:
        return None
    return (info.st_mtime_ns, info.st_size)


def _wal_path(path: Path) -> Path:
    return path.with_name(path.name + "-wal")


@dataclass(frozen=True)
class _LoadedAccount:
    """One `accounts` row and its latest value, before `now` or a profile category is applied."""
    id: str
    label: str
    institution: str
    type_code: str
    type_display: str
    value: float
    cash: float
    day: str | None  # the value's as-of day; None only for an account with neither a snapshot nor a history point
    flows: str  # 'balance': no transactions explain its changes, so every change is money moved
    credit_limit: float | None
    rate_pct: float | None
    available: float | None  # the latest cash row's remaining credit, when the bank reported one


@dataclass(frozen=True)
class _Loaded:
    """Everything a snapshot needs from the warehouse: plain data, with no `now` and no profile category baked in,
    so it is safe to cache and reuse across connector instances that share a warehouse."""
    accounts: list[_LoadedAccount]
    series: list[Series]
    holdings: list[Holding]
    left_out: int
    prices_to: str | None
    benchmark_rows: list[tuple[str, float]]
    last_success: datetime | None


_clock = _time.monotonic  # a module-level seam a test can replace
# the file state can miss a same-size write within one timestamp tick; a minute bounds how stale a read can be
CACHE_SECONDS = 60

_CACHE_LOCK = threading.Lock()
# resolved warehouse path -> (the state it was loaded at, when it was loaded, the data). One entry per path; the
# server serves requests from a thread pool, so the dict itself is guarded, but a load's disk I/O runs outside it.
_CACHE: dict[Path, tuple[tuple, float, _Loaded]] = {}


class FdcConnector:
    """Reads one warehouse. `categories` maps an account id or exact label to a category; `benchmark` is looked up
    in the warehouse's prices."""

    def __init__(self, source_id: str, label: str, path: Path, categories: dict[str, str] | None = None,
                 benchmark: BenchmarkCfg | None = None, timeout: float = TIMEOUT) -> None:
        self.source_id = source_id
        self.label = label
        self.path = path
        self.categories = dict(categories or {})
        self.benchmark = benchmark
        self.timeout = timeout

    def snapshot(self, now: datetime) -> Snapshot:
        return self._build(self._load(), now)

    def _category(self, account_id: str, label: str, account_type: str) -> Category:
        chosen = self.categories.get(account_id) or self.categories.get(label)
        return cast(Category, chosen) if chosen else category_of(account_type)

    def _benchmark_symbol(self) -> str | None:
        # the collector stores tickers upper-case; match its `symbol = ?` index however the profile wrote it
        return self.benchmark.symbol.upper() if self.benchmark else None

    def _load(self) -> _Loaded:
        """The warehouse's data, from the cache when the file (and its WAL side file) haven't changed since the
        cached load and that load is under CACHE_SECONDS old, else freshly read and cached. A load that raises is
        never cached; a missing file is still "no warehouse at <path>", raised by `connect` before any of this."""
        resolved = self.path.resolve()
        key = (resolved, _file_state(resolved), _file_state(_wal_path(resolved)), self._benchmark_symbol())
        with _CACHE_LOCK:
            cached = _CACHE.get(resolved)
            if cached is not None and cached[0] == key and _clock() - cached[1] < CACHE_SECONDS:
                return cached[2]
        try:
            with connect(self.path, self.timeout) as conn:
                check_schema(conn, self.path)
                data = self._read(conn)
        except sqlite3.Error as exc:
            raise ConnectorError(f"the warehouse couldn't be read: {exc}") from None
        with _CACHE_LOCK:
            _CACHE[resolved] = (key, _clock(), data)
        return data

    def _read(self, conn: sqlite3.Connection) -> _Loaded:
        rows = conn.execute("SELECT id, label, institution, account_type, flows, credit_limit, rate_pct "
                            "FROM accounts ORDER BY id").fetchall()
        ids = dict(zip((r[0] for r in rows), account_ids([r[1] for r in rows])))
        by_label = {r[1]: ids[r[0]] for r in rows}
        # the latest daily value of each account; SQLite takes the bare columns from the row MAX() picked
        latest = {label: (day, total, cash) for label, day, total, cash in conn.execute(
            "SELECT account, MAX(as_of_date), total, cash FROM account_values_daily GROUP BY account")}
        # the latest cash row's available credit per account (days ascending, so the last one wins)
        available: dict[int, float | None] = {}
        for account, value in conn.execute("SELECT account_id, available FROM cash_balances ORDER BY as_of_date"):
            available[account] = value
        replayed = history(conn)
        days = {warehouse_id: _with_snapshot(replayed.get(warehouse_id, []), latest.get(label))
                for warehouse_id, label, *_ in rows}
        # money moved is filed under the replayed days and a newer snapshot's day; an account with no replayed
        # history has no days to file it under
        moved = flows(conn, {account: [day for day, _, _ in points] for account, points in days.items()
                             if replayed.get(account)})
        for warehouse_id, _, _, _, flow_kind, _, _ in rows:
            if flow_kind == "balance":  # every change is money moved; the first point moves nothing
                points = days[warehouse_id]
                moved[warehouse_id] = {day: (value - points[i - 1][1] if i else 0.0)
                                       for i, (day, value, _) in enumerate(points)}

        accounts: list[_LoadedAccount] = []
        series: list[Series] = []
        for warehouse_id, label, institution, kind, flow_kind, credit_limit, rate_pct in rows:
            points = days[warehouse_id]
            if points:
                series.append(Series(id=ids[warehouse_id], points=[
                    ValuePoint(date=date.fromisoformat(day), value=round(value, 2),
                               net_flow=round(moved[warehouse_id].get(day, 0.0), 2))
                    for day, value, _ in points]))
            day, value, cash = points[-1] if points else (None, 0.0, 0.0)
            accounts.append(_LoadedAccount(
                id=ids[warehouse_id], label=label, institution=institution_text(institution),
                type_code=kind, type_display=type_text(kind), value=round(value, 2), cash=round(cash, 2), day=day,
                flows=flow_kind, credit_limit=credit_limit, rate_pct=rate_pct, available=available.get(warehouse_id),
            ))

        holdings, left_out = self._holdings(conn, by_label)
        first = min((s.points[0].date for s in series), default=None)
        benchmark_rows = self._benchmark_rows(conn, first)
        # each security's last price through the prices index: MAX(date) over the whole table is a full scan
        priced = conn.execute("SELECT MAX((SELECT MAX(date) FROM prices WHERE symbol = s.symbol)) "
                              "FROM securities s").fetchone()[0]
        return _Loaded(accounts=accounts, series=series, holdings=holdings, left_out=left_out, prices_to=priced,
                       benchmark_rows=benchmark_rows, last_success=last_success(conn))

    def _build(self, data: _Loaded, now: datetime) -> Snapshot:
        accounts: list[Account] = []
        debt_ids: set[str] = set()
        for a in data.accounts:
            category = self._category(a.id, a.label, a.type_code)
            value, cash = a.value, a.cash
            limit = a.credit_limit
            if category == "debt":  # the collector stores what a debt owes below zero; the contract wants it owed
                debt_ids.add(a.id)
                value, cash = -value, -cash
                # a card's remaining credit tells what its line is; 0, none or below zero tells nothing
                if limit is None and a.available is not None and a.available > 0:
                    limit = round(value + a.available, 2)
            accounts.append(Account(
                id=a.id, name=a.label, institution=a.institution, account_type=a.type_display, category=category,
                value=value, cash=cash, as_of=_close(a.day) if a.day else now, rate_pct=a.rate_pct, limit=limit))
        # a debt's history is what it owed each day; its flow keeps its meaning (the contract's): money in, a
        # payment, less money out, a charge. The stored balance's own change is already that, so only the value turns
        history = [Series(id=s.id, points=[ValuePoint(date=p.date, value=-p.value, net_flow=p.net_flow)
                                            for p in s.points]) if s.id in debt_ids else s
                   for s in data.series]
        notes = [_plural(len(accounts), "account"), _plural(len(data.holdings), "holding"),
                 f"prices to {_day(data.prices_to)}" if data.prices_to else "no prices yet"]
        if data.left_out:
            notes.append(f"{_plural(data.left_out, 'holding')} left out (no market value)")
        benchmark = None
        if self.benchmark is not None:
            if data.benchmark_rows:
                benchmark = Benchmark(symbol=self.benchmark.symbol, label=self.benchmark.label,
                                      points=[ValuePoint(date=date.fromisoformat(day), value=value)
                                              for day, value in data.benchmark_rows])
            else:
                notes.append(f"no {self.benchmark.symbol} prices in the warehouse")
        unmatched = sorted(set(self.categories) - {a.id for a in accounts} - {a.name for a in accounts})
        if unmatched:
            notes.append(f"no account matches categories {', '.join(repr(k) for k in unmatched)}")
        source = Source(id=self.source_id, label=self.label, kind="fdc", last_success=data.last_success,
                        status="ok" if data.last_success else "stale", detail=" · ".join(notes))
        return Snapshot(generated_at=now, sources=[source], accounts=accounts, holdings=data.holdings,
                        account_history=history, benchmark=benchmark)

    def _holdings(self, conn: sqlite3.Connection, by_label: dict[str, str]) -> tuple[list[Holding], int]:
        """The latest snapshot's positions, largest first in each account, each with its snapshot's day, and how
        many had no market value (they are left out: there is nothing to add up)."""
        holdings: list[Holding] = []
        left_out = 0
        for day, label, symbol, name, quantity, price, value, cost in conn.execute(
                "SELECT as_of_date, account, symbol, description, quantity, price, market_value, cost_basis_total "
                "FROM positions_latest"):
            if value is None:
                left_out += 1
                continue
            if price is None:
                price = value / quantity if quantity else 0.0
            holdings.append(Holding(account_id=by_label[label], symbol=symbol, name=name or "", quantity=quantity,
                                    price=price, value=round(value, 2),
                                    cost_basis=round(cost, 2) if cost is not None else None,
                                    as_of=date.fromisoformat(day)))
        rank = {account_id: i for i, account_id in enumerate(by_label.values())}
        holdings.sort(key=lambda h: (rank[h.account_id], -h.value))
        return holdings, left_out

    def _benchmark_rows(self, conn: sqlite3.Connection, first: date | None) -> list[tuple[str, float]]:
        """The profile's benchmark from the warehouse's prices (adjusted, so dividends count, as they do in the
        accounts), from the last close on or before the first day of account history."""
        if self.benchmark is None:
            return []
        rows = conn.execute("SELECT date, adj_close FROM prices WHERE symbol = ? ORDER BY date",
                            (self._benchmark_symbol(),)).fetchall()
        if first is not None:
            rows = rows[max((i for i, (day, _) in enumerate(rows) if day <= first.isoformat()), default=0):]
        return rows
