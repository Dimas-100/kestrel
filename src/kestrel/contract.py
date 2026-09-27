"""The kestrel data contract, version 1.

Every connector returns a Snapshot. A private system plugs in by serving a Snapshot as JSON (the feed connector).
Within a major version changes are additive only, so unknown fields are ignored and a newer minor still loads.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

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
    account_type: str = ""  # display text for the kind of account: "Roth IRA", "Brokerage"
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
    as_of: dt.date | None = None  # the day the holding was reported, which can be older than its account's value


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
    cagr_pct: float | None = None  # the backtest's yearly return
    max_drawdown_pct: float | None = None  # the backtest's worst drop, negative


class WatchItem(Model):
    """A name close to a signal, for "Where the money works"."""

    symbol: str
    label: str  # what is measured, e.g. "RSI(2)"
    value: float | None = None
    note: str = ""


class Strategy(Model):
    id: str
    name: str
    summary: str = ""
    steps: list[Step] = []
    sizing: str = ""
    expected: Expected | None = None
    review_at_trades: int | None = None
    watch: list[WatchItem] = []


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


class Bar(Model):
    date: dt.date
    open: float
    high: float
    low: float
    close: float


class IndicatorLine(Model):
    value: float
    label: str  # "buy under 10"


class Indicator(Model):
    label: str  # "RSI(2)"
    values: list[float | None]  # aligned with the chart's bars; None where it isn't defined yet
    lines: list[IndicatorLine] = []  # thresholds, drawn dotted


class TradeChart(Model):
    """Daily bars around one closed trade. It matches a Trade by (book_id, symbol, opened); a chart whose bars
    don't include the open date, or that matches no trade, is ignored."""

    book_id: str
    symbol: str
    opened: dt.date
    bars: list[Bar]
    indicator: Indicator | None = None
    stop: float | None = None


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
    # a page inside kestrel ("/books"), or empty: never another site, including "//host" and "/\host",
    # which browsers read as a link to another host
    link: str = Field(default="", pattern=r"^(/([^/\\\s].*)?)?$")


class Benchmark(Model):
    symbol: str
    label: str
    points: list[ValuePoint]  # value = the close


def check_version(value: str) -> str:
    """`value` when its major version is this contract's; a ValueError worded for a person when it isn't."""
    if value.split(".")[0] != CONTRACT_VERSION:
        raise ValueError(f"unsupported contract version {value!r}; this kestrel reads major version {CONTRACT_VERSION}")
    return value


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
    trade_charts: list[TradeChart] = []
    strategies: list[Strategy] = []
    runs: list[Run] = []
    alerts: list[Alert] = []
    benchmark: Benchmark | None = None

    @field_validator("contract_version")
    @classmethod
    def _same_major(cls, value: str) -> str:
        return check_version(value)


_LIST_FIELDS = (
    "sources", "accounts", "holdings", "account_history", "books", "book_history",
    "positions", "trades", "trade_charts", "strategies", "runs", "alerts",
)


def merge(snapshots: list[Snapshot], generated_at: dt.datetime) -> Snapshot:
    """Combine the snapshots of several connectors into one. The first benchmark found wins."""
    fields: dict[str, object] = {name: [item for s in snapshots for item in getattr(s, name)] for name in _LIST_FIELDS}
    fields["benchmark"] = next((s.benchmark for s in snapshots if s.benchmark is not None), None)
    return Snapshot(generated_at=generated_at, **fields)
