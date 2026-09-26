"""The Accounts pages, computed from one Snapshot: what does each account hold, and how much of its growth was my
deposits vs the market?"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from ..contract import Category, Holding, Snapshot, ValuePoint
from ..metrics import sum_series
from ..profile import Profile
from .home import View, _day_pct

Window = Literal["ytd", "1y", "all"]
WINDOWS: tuple[Window, ...] = ("ytd", "1y", "all")
FLOWS = 8  # "Money in and out" lists the last eight


class Growth(View):
    start_date: dt.date  # the day the starting value is from
    start: float
    deposits: float  # deposits minus withdrawals after the start, up to the end
    market: float  # the rest of the change: end - start - deposits
    end: float


class AccountLine(View):
    id: str
    name: str
    institution: str
    account_type: str
    category: Category
    value: float
    share: float | None  # percent of all accounts
    day_change: float | None  # the last day's change, net of that day's deposits
    day_pct: float | None
    year_market: float | None  # this year's market growth


class CombinedHolding(View):
    symbol: str  # empty on the cash row
    name: str
    cash: bool
    value: float
    share: float | None  # percent of everything held, cash included
    accounts: list[str]  # the names of the accounts that hold it, alphabetical


class AccountsView(View):
    as_of: dt.datetime
    count: int
    total: float
    growth: dict[Window, Growth | None]  # all accounts together
    accounts: list[AccountLine]  # largest first
    holdings: list[CombinedHolding]  # largest first


class Flow(View):
    date: dt.date
    amount: float  # positive in, negative out


class HoldingRow(View):
    symbol: str
    name: str
    quantity: float
    price: float
    value: float
    weight: float | None  # percent of the account: its holdings plus its cash
    cost_basis: float | None
    gain: float | None
    gain_pct: float | None


class Totals(View):
    value: float  # the holdings plus the cash
    cost_basis: float | None  # of the holdings whose cost is known
    gain: float | None
    gain_pct: float | None
    unknown_cost: int  # holdings left out of the cost and gain totals


class AccountView(View):
    id: str
    name: str
    institution: str
    account_type: str
    category: Category
    value: float
    as_of: dt.date  # the day the value is from
    points: list[ValuePoint]
    growth: dict[Window, Growth | None]
    flows: list[Flow]  # the last eight days money moved, newest first
    holdings: list[HoldingRow]  # largest first
    holdings_as_of: dt.date | None  # the latest day the holdings were reported; None when the source doesn't say
    cash: float
    cash_weight: float | None
    totals: Totals


def window_start(window: Window, today: dt.date, points: list[ValuePoint]) -> dt.date:
    """This year: 1 January; 1 year: a year ago today; all: the first point."""
    if window == "ytd":
        return dt.date(today.year, 1, 1)
    if window == "1y":
        return today - dt.timedelta(days=365)
    return points[0].date if points else today


def growth(points: list[ValuePoint], start: dt.date) -> Growth | None:
    """From the value held on `start` (the last point on or before it, or the first point when history begins
    later) to the last point. Fewer than two points is no growth."""
    first = max((i for i, p in enumerate(points) if p.date <= start), default=0)
    window = points[first:]
    if len(window) < 2:
        return None
    begin, end = window[0].value, window[-1].value
    deposits = sum(p.net_flow for p in window[1:])
    return Growth(start_date=window[0].date, start=round(begin, 2), deposits=round(deposits, 2),
                  market=round(end - begin - deposits, 2), end=round(end, 2))


def growths(points: list[ValuePoint], today: dt.date) -> dict[Window, Growth | None]:
    return {w: growth(points, window_start(w, today, points)) for w in WINDOWS}


def _share(value: float, whole: float) -> float | None:
    """A percent of a positive whole; none of a whole that is zero or less (every account closed, or a debit bigger
    than what is held)."""
    return round(value / whole * 100, 2) if whole > 0 else None


def _history(snapshot: Snapshot) -> dict[str, list[ValuePoint]]:
    return {s.id: list(s.points) for s in snapshot.account_history}


def combined_holdings(snapshot: Snapshot) -> list[CombinedHolding]:
    """Every holding added up by symbol across accounts, and one row for all the cash; largest first."""
    names = {a.id: a.name for a in snapshot.accounts}
    by_symbol: dict[str, list[Holding]] = {}
    for h in snapshot.holdings:
        by_symbol.setdefault(h.symbol, []).append(h)
    cash = sum(a.cash for a in snapshot.accounts)
    whole = sum(h.value for h in snapshot.holdings) + cash
    rows = [
        CombinedHolding(symbol=symbol, name=next((h.name for h in held if h.name), ""), cash=False,
                        value=round(sum(h.value for h in held), 2), share=_share(sum(h.value for h in held), whole),
                        accounts=sorted({names.get(h.account_id, h.account_id) for h in held}))
        for symbol, held in by_symbol.items()
    ]
    holders = sorted(a.name for a in snapshot.accounts if round(a.cash, 2) != 0)
    if holders:
        rows.append(CombinedHolding(symbol="", name="Cash", cash=True, value=round(cash, 2), share=_share(cash, whole),
                                    accounts=holders))
    return sorted(rows, key=lambda r: (-r.value, r.symbol))


def accounts_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> AccountsView:
    today = now.astimezone(profile.tz).date()
    history = _history(snapshot)
    total = sum(a.value for a in snapshot.accounts)
    rows = []
    for a in snapshot.accounts:
        points = history.get(a.id, [])
        year = growth(points, window_start("ytd", today, points))
        rows.append(AccountLine(
            id=a.id, name=a.name, institution=a.institution, account_type=a.account_type, category=a.category,
            value=a.value, share=_share(a.value, total),
            day_change=round(points[-1].value - points[-2].value - points[-1].net_flow, 2) if len(points) > 1 else None,
            day_pct=_day_pct(points), year_market=year.market if year else None,
        ))
    rows.sort(key=lambda r: (-r.value, r.name))
    everything = sum_series([history[a.id] for a in snapshot.accounts if a.id in history])
    return AccountsView(as_of=now, count=len(rows), total=round(total, 2), growth=growths(everything, today),
                        accounts=rows, holdings=combined_holdings(snapshot))


def _row(h: Holding, whole: float) -> HoldingRow:
    gain = round(h.value - h.cost_basis, 2) if h.cost_basis is not None else None
    return HoldingRow(symbol=h.symbol, name=h.name, quantity=h.quantity, price=h.price, value=h.value,
                      weight=_share(h.value, whole), cost_basis=h.cost_basis, gain=gain,
                      gain_pct=round((h.value - h.cost_basis) / h.cost_basis * 100, 2) if h.cost_basis else None)


def account_view(snapshot: Snapshot, profile: Profile, now: dt.datetime, account_id: str) -> AccountView | None:
    """One account, or None when there is no account with that id."""
    account = next((a for a in snapshot.accounts if a.id == account_id), None)
    if account is None:
        return None
    today = now.astimezone(profile.tz).date()
    points = _history(snapshot).get(account.id, [])
    held = sorted((h for h in snapshot.holdings if h.account_id == account.id), key=lambda h: (-h.value, h.symbol))
    whole = sum(h.value for h in held) + account.cash
    known = [(h.value, h.cost_basis) for h in held if h.cost_basis is not None]
    cost = sum(c for _, c in known) if known else None
    gain = sum(v - c for v, c in known) if known else None
    return AccountView(
        id=account.id, name=account.name, institution=account.institution, account_type=account.account_type,
        category=account.category, value=account.value, as_of=account.as_of.date(), points=points,
        growth=growths(points, today),
        flows=[Flow(date=p.date, amount=p.net_flow) for p in reversed(points) if round(p.net_flow, 2) != 0][:FLOWS],
        holdings=[_row(h, whole) for h in held], holdings_as_of=max((h.as_of for h in held if h.as_of), default=None),
        cash=account.cash, cash_weight=_share(account.cash, whole),
        totals=Totals(value=round(whole, 2), cost_basis=round(cost, 2) if cost is not None else None,
                      gain=round(gain, 2) if gain is not None else None,
                      gain_pct=round(gain / cost * 100, 2) if cost and gain is not None else None,
                      unknown_cost=len(held) - len(known)),  # the gain totals leave these out
    )
