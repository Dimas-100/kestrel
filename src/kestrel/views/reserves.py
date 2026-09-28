"""The Reserves page, computed from one Snapshot: what cash sits where, what is owed on a credit line, and how the
best rate earned compares with the worst rate paid."""

from __future__ import annotations

import datetime as dt

from ..contract import Snapshot
from ..profile import Profile
from ._base import View


class CashLine(View):
    id: str
    name: str
    institution: str
    value: float
    rate_pct: float | None
    as_of: dt.date


class DebtLine(View):
    id: str
    name: str
    institution: str
    owed: float  # a credit balance (paid past zero) shows below zero
    limit: float | None
    utilization_pct: float | None  # owed (clamped at 0) over the limit; None without one
    rate_pct: float | None
    as_of: dt.date


class Totals(View):
    cash: float
    owed: float
    net: float  # cash minus owed
    utilization_pct: float | None  # over every debt with a limit


class Spread(View):
    owed_rate_pct: float  # the highest APR among debts with a balance
    earned_rate_pct: float  # the best cash APY
    yearly_cost: float  # sum of each debt's own balance times its own rate
    yearly_earned: float  # sum of each cash account's own balance times its own rate
    gap: float  # yearly_earned minus yearly_cost


class ReservesView(View):
    as_of: dt.datetime
    cash: list[CashLine]
    debts: list[DebtLine]
    totals: Totals
    spread: Spread | None  # None without both a rated debt balance and a rated cash balance


def reserves_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> ReservesView:
    cash = sorted(
        (CashLine(id=a.id, name=a.name, institution=a.institution, value=round(a.value, 2), rate_pct=a.rate_pct,
                 as_of=a.as_of.date()) for a in snapshot.accounts if a.category == "cash"),
        key=lambda c: (-c.value, c.name),
    )
    # a limit of 0 is treated the same as no limit (there is nothing to divide by): utilization is None, not 0%
    debts = sorted(
        (DebtLine(id=a.id, name=a.name, institution=a.institution, owed=round(a.value, 2), limit=a.limit,
                 utilization_pct=round(max(a.value, 0.0) / a.limit * 100, 2) if a.limit else None,
                 rate_pct=a.rate_pct, as_of=a.as_of.date()) for a in snapshot.accounts if a.category == "debt"),
        key=lambda d: (-d.owed, d.name),
    )
    total_cash = round(sum(c.value for c in cash), 2)
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
        yearly_cost = round(sum(d.owed * d.rate_pct / 100 for d in debts_rated), 2)
        yearly_earned = round(sum(c.value * c.rate_pct / 100 for c in cash_rated), 2)
        spread = Spread(owed_rate_pct=max(d.rate_pct for d in debts_rated),
                        earned_rate_pct=max(c.rate_pct for c in cash_rated), yearly_cost=yearly_cost,
                        yearly_earned=yearly_earned, gap=round(yearly_earned - yearly_cost, 2))
    return ReservesView(as_of=now, cash=cash, debts=debts, totals=totals, spread=spread)
