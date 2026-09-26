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