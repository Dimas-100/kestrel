"""The Reserves page, computed from one Snapshot: what cash sits where, what is owed on a credit line, and how the
best rate earned compares with the worst rate paid."""

from __future__ import annotations

import datetime as dt

from ..contract import Snapshot, Transaction
from ..profile import Profile
from ._base import View

MONTH_DAYS = 30.4375
MIN_RUNWAY_DAYS = 14  # fewer days of bank rows than this say nothing reliable about the pace


class CashLine(View):
    id: str
    name: str
    institution: str
    value: float
    rate_pct: float | None
    as_of: dt.date
    share_pct: float | None  # of all the cash; None when there is none


class DebtLine(View):
    id: str
    name: str
    institution: str
    owed: float  # a credit balance (paid past zero) shows below zero
    limit: float | None
    utilization_pct: float | None  # owed (clamped at 0) over the limit; None without one
    rate_pct: float | None
    as_of: dt.date
    yearly_cost: float | None  # a year of interest at this balance and rate; None without a rate or a balance owed


class Totals(View):
    cash: float
    owed: float
    net: float  # cash minus owed
    utilization_pct: float | None  # over every debt with a limit


class Spread(View):
    owed_rate_pct: float  # the highest APR among debts with a balance
    owed_name: str  # the debt that rate is on
    earned_rate_pct: float  # the best cash APY
    # a year of each, shown apart and never netted: interest paid and interest earned are different money
    yearly_cost: float  # sum of each debt's own balance times its own rate
    yearly_earned: float  # sum of each cash account's own balance times its own rate
    # paying the dearest debt from cash: only when it costs more than the best cash earns and there is cash
    pay_down: float | None  # the smaller of what that debt owes and all the cash
    pay_down_saves: float | None  # pay_down x (owed_rate_pct - earned_rate_pct) / 100: a year's interest saved


class Runway(View):
    """How long the cash would last at the pace money has left the cash accounts: every outflow posted on a cash
    account over the window (transfers into investments and card payments included, so the figure is the honest,
    conservative one), scaled to a month."""
    months: float
    monthly_out: float
    days: int  # the window: from the oldest to the newest row on any cash account, inclusive
    since: dt.date
    # the band of the first ratio target whose label contains "runway" (the investing feed's "Cash runway")
    aim: float | None
    low: float | None
    high: float | None


class MonthFlow(View):
    month: str  # "2026-09"
    money_in: float
    money_out: float  # as a positive amount


class ReservesView(View):
    as_of: dt.datetime
    summary: str  # the header's sentence: cash after debts, and how long it would last when the pace is known
    runway: Runway | None
    flows: list[MonthFlow]  # one per calendar month with rows on a cash account, ascending
    cash: list[CashLine]
    debts: list[DebtLine]
    totals: Totals
    spread: Spread | None  # None without both a rated debt balance and a rated cash balance


def _money_text(value: float) -> str:
    return f"${value:,.2f}"


def runway_of(rows: list[Transaction], total_cash: float, snapshot: Snapshot) -> Runway | None:
    """The runway from the cash accounts' rows (§2.1), or None without enough of them or any money out."""
    if not rows:
        return None
    days = (max(r.date for r in rows) - min(r.date for r in rows)).days + 1
    out = -sum(r.amount for r in rows if r.amount < 0)
    if days < MIN_RUNWAY_DAYS or out <= 0:
        return None
    monthly_out = round(out / days * MONTH_DAYS, 2)
    band = next((t for t in snapshot.targets if t.unit == "x" and "runway" in t.label.lower()), None)
    return Runway(months=round(total_cash / monthly_out, 1), monthly_out=monthly_out, days=days,
                  since=min(r.date for r in rows), aim=band.target if band else None, low=band.low if band else None,
                  high=band.high if band else None)


def flows_of(rows: list[Transaction]) -> list[MonthFlow]:
    """Money in and out per calendar month over the cash accounts' rows, ascending."""
    by_month: dict[str, list[float]] = {}
    for r in rows:
        month = r.date.strftime("%Y-%m")
        totals = by_month.setdefault(month, [0.0, 0.0])
        if r.amount > 0:
            totals[0] += r.amount
        else:
            totals[1] -= r.amount
    return [MonthFlow(month=m, money_in=round(i, 2), money_out=round(o, 2)) for m, (i, o) in sorted(by_month.items())]


def reserves_summary(net: float, runway: Runway | None) -> str:
    text = f"{_money_text(net)} in cash after debts."
    if runway is not None:
        text += (f" At the pace money has left your cash these {runway.days} days, it would last about "
                 f"{runway.months:.1f} months.")
    return text


def reserves_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> ReservesView:
    cash_accounts = [a for a in snapshot.accounts if a.category == "cash"]
    total_cash = round(sum(a.value for a in cash_accounts), 2)
    cash = sorted(
        (CashLine(id=a.id, name=a.name, institution=a.institution, value=round(a.value, 2), rate_pct=a.rate_pct,
                 as_of=a.as_of.date(),
                 share_pct=round(a.value / total_cash * 100, 2) if total_cash > 0 else None) for a in cash_accounts),
        key=lambda c: (-c.value, c.name),
    )
    # a limit of 0 is treated the same as no limit (there is nothing to divide by): utilization is None, not 0%
    debts = sorted(
        (DebtLine(id=a.id, name=a.name, institution=a.institution, owed=round(a.value, 2), limit=a.limit,
                 utilization_pct=round(max(a.value, 0.0) / a.limit * 100, 2) if a.limit else None,
                 rate_pct=a.rate_pct, as_of=a.as_of.date(),
                 yearly_cost=round(a.value * a.rate_pct / 100, 2) if a.rate_pct is not None and a.value > 0 else None)
         for a in snapshot.accounts if a.category == "debt"),
        key=lambda d: (-d.owed, d.name),
    )
    # SIGNED: a credit balance (below zero) offsets real debt, exactly as it offsets net worth on Home — only
    # utilization clamps a line at 0, because a credit balance uses none of a credit line
    total_owed = round(sum(d.owed for d in debts), 2)
    limited = [d for d in debts if d.limit]
    utilization = (round(sum(max(d.owed, 0.0) for d in limited) / sum(d.limit for d in limited) * 100, 2)
                  if limited else None)
    totals = Totals(cash=total_cash, owed=total_owed, net=round(total_cash - total_owed, 2),
                    utilization_pct=utilization)

    debts_rated = [d for d in debts if d.owed > 0 and d.rate_pct is not None]
    cash_rated = [c for c in cash if c.rate_pct is not None]
    spread = None
    if debts_rated and cash_rated:
        dearest = max(debts_rated, key=lambda d: d.rate_pct)  # the first of a tie: the largest balance
        best = max(c.rate_pct for c in cash_rated)
        # the cash rate given up is the best one: the saving is never overstated
        pay_down = round(min(dearest.owed, total_cash), 2) if dearest.rate_pct > best and total_cash > 0 else None
        spread = Spread(
            owed_rate_pct=dearest.rate_pct, owed_name=dearest.name, earned_rate_pct=best,
            yearly_cost=round(sum(d.owed * d.rate_pct / 100 for d in debts_rated), 2),
            yearly_earned=round(sum(c.value * c.rate_pct / 100 for c in cash_rated), 2), pay_down=pay_down,
            pay_down_saves=round(pay_down * (dearest.rate_pct - best) / 100, 2) if pay_down is not None else None,
        )
    cash_ids = {a.id for a in cash_accounts}
    rows = [t for t in snapshot.transactions if t.account_id in cash_ids]
    runway = runway_of(rows, total_cash, snapshot)
    return ReservesView(as_of=now, summary=reserves_summary(totals.net, runway), runway=runway, flows=flows_of(rows),
                        cash=cash, debts=debts, totals=totals, spread=spread)
