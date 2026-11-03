"""The Reserves page, computed from one Snapshot: what cash sits where, what is owed on a credit line, and how the
best rate earned compares with the worst rate paid."""

from __future__ import annotations

import datetime as dt
import math
import re
from collections import defaultdict
from typing import Literal

from ..contract import Account, Snapshot, Transaction
from ..profile import Profile
from ._base import View

MONTH_DAYS = 30.4375
MIN_RUNWAY_DAYS = 14  # fewer days of bank rows than this say nothing reliable about the pace
MOVE_DAYS = 3  # the two sides of a move between your own cash accounts post at most this many days apart
SHORT_DAYS = 60  # coverage under this many days reads in days, from it in months
STALE_DAYS = 7  # a balance or the newest bank row older than this (against the view's day) is named
# a row's own words that say money moved rather than was spent: "Online Banking transfer", "Zelle payment to",
# "Withdrawal to Rainy Day Fund", "Deposit from Checking"
TRANSFER_WORDS = re.compile(r"\b(transfer|xfer|zelle|withdrawal to|deposit from)\b", re.IGNORECASE)
# words too common in bank rows to say two of them name the same party
PLAIN_WORDS = {"from", "with", "payment", "deposit", "withdrawal", "transfer", "online", "banking", "mobile", "conf",
               "confirmation", "checking", "savings", "account", "bank", "zelle", "card", "purchase", "recurring"}


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
    owed: float  # recorded debt: what the feeds know is owed
    net: float  # cash minus owed
    utilization_pct: float | None  # over every debt with a limit
    cash_count: int
    debt_count: int
    limited_count: int  # the debts with a limit on record: what utilization_pct is over
    oldest_as_of: dt.date | None  # the oldest and newest balance among cash and debt; None without either
    newest_as_of: dt.date | None
    stale: list[str]  # cash and debt lines whose balance is over STALE_DAYS old, oldest first


class Rates(View):
    """How much of what is owed, and of the cash, has a rate on record: every interest figure covers that part only."""
    owed: float  # positive balances owed (a credit balance owes nothing)
    rated_owed: float  # of which a line carries an APR
    rated_owed_pct: float | None  # None when nothing is owed
    unrated: list[str]  # the lines with a balance owed and no APR, largest balance first
    cash: float
    rated_cash: float  # of the cash, on accounts that carry an APY


class Spread(View):
    owed_rate_pct: float  # the highest APR on record among debts with a balance
    owed_name: str  # the debt that rate is on
    earned_rate_pct: float  # the best cash APY on record
    # a year of each, shown apart and never netted: interest paid and interest earned are different money
    yearly_cost: float  # sum of each debt's own balance times its own rate
    yearly_earned: float  # sum of each cash account's own balance times its own rate
    # paying the dearest debt from cash: only when it costs more than the best cash earns and there is cash
    pay_down: float | None  # the smaller of what that debt owes and all the cash
    pay_down_saves: float | None  # pay_down x (owed_rate_pct - earned_rate_pct) / 100: a year's interest saved


class Runway(View):
    """How long the cash would last at the pace money has left the cash accounts: every outflow posted on a cash
    account over the window except a move between two of them (spec 2026-10-08 §2) -- money to a card, a brokerage or
    a person still counts, so the figure stays the conservative one. Income is not netted against it."""
    unit: Literal["days", "months"]  # how the figure reads: days under SHORT_DAYS
    days_cover: int  # today's cash over the pace per day, rounded down; never below 0
    months: float  # the same in months, to one decimal; never below 0
    daily_out: float
    monthly_out: float
    days: int  # the window: from the oldest to the newest row on any cash account, inclusive
    since: dt.date
    through: dt.date  # the newest row
    stale: bool  # the newest row is over STALE_DAYS older than the view's day
    moved: float  # what moved between your own cash accounts in the window (one side of each pair): left out
    moved_count: int  # how many pairs
    # the band of the first ratio target whose label contains "runway" (the investing feed's "Cash runway")
    aim: float | None
    low: float | None
    high: float | None


class MonthFlow(View):
    month: str  # "2026-09"
    money_in: float  # moves between your own cash accounts left out of both
    money_out: float  # as a positive amount
    net: float  # money_in - money_out
    moved: float  # what moved between your own cash accounts this month (dated by the side that left), left out
    start: dt.date  # the first and last day of the month the window covers
    end: dt.date
    days: int
    partial: bool  # the window doesn't cover the whole month: the first month, or the current one (month to date)


class ReservesView(View):
    as_of: dt.datetime
    today: dt.date  # the view's day in the profile's zone: what "stale" and "month to date" are measured against
    summary: str  # the header's sentence: cash after debts, and how long it would last when the pace is known
    runway: Runway | None
    flows: list[MonthFlow]  # one per calendar month with rows on a cash account, ascending
    cash: list[CashLine]
    debts: list[DebtLine]
    totals: Totals
    spread: Spread | None  # None without both a rated debt balance and a rated cash balance
    rates: Rates | None  # None with no debt and no cash at all


def _money_text(value: float) -> str:
    return f"${value:,.2f}"


def _reads_as_transfer(r: Transaction) -> bool:
    return "transfer" in r.category.lower() or bool(TRANSFER_WORDS.search(f"{r.description} {r.counterparty}"))


def _words(r: Transaction) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", f"{r.description} {r.counterparty}".lower()) if w not in PLAIN_WORDS}


def _corroborated(a: Transaction, b: Transaction) -> bool:
    """Both sides read as a transfer, or one does and the other names the same party (a Zelle to yourself arrives as
    your name): round amounts are common, so the same amount on the same day alone is not enough."""
    ta, tb = _reads_as_transfer(a), _reads_as_transfer(b)
    return (ta and tb) or ((ta or tb) and bool(_words(a) & _words(b)))


def moves_of(rows: list[Transaction], accounts: list[Account]) -> list[tuple[int, int]]:
    """The moves between your own cash accounts among `rows` (all on cash accounts), as (out, in) index pairs (spec
    2026-10-08 §2): equal and opposite to the cent, on two different accounts, at most MOVE_DAYS apart, and
    corroborated by their words; closest date first, then a pair at the same bank, each row in at most one pair."""
    bank = {a.id: a.institution for a in accounts}
    ins: dict[int, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        if r.amount > 0:
            ins[round(r.amount * 100)].append(i)
    candidates = sorted(
        (abs((rows[i].date - r.date).days), bank.get(rows[i].account_id) != bank.get(r.account_id), r.date, o, i)
        for o, r in enumerate(rows) if r.amount < 0
        for i in ins.get(round(-r.amount * 100), ())
        if rows[i].account_id != r.account_id and abs((rows[i].date - r.date).days) <= MOVE_DAYS
        and _corroborated(r, rows[i])
    )
    used: set[int] = set()
    pairs = []
    for *_, o, i in candidates:
        if o not in used and i not in used:
            used.update((o, i))
            pairs.append((o, i))
    return pairs


def runway_of(rows: list[Transaction], pairs: list[tuple[int, int]], total_cash: float, snapshot: Snapshot,
              today: dt.date) -> Runway | None:
    """The runway from the cash accounts' rows (spec 2026-10-08 §2), or None without enough of them or any money out
    that wasn't a move between them."""
    if not rows:
        return None
    since, through = min(r.date for r in rows), max(r.date for r in rows)
    days = (through - since).days + 1
    moved_ids = {k for pair in pairs for k in pair}
    out = -sum(r.amount for k, r in enumerate(rows) if r.amount < 0 and k not in moved_ids)
    if days < MIN_RUNWAY_DAYS or out <= 0:
        return None
    per_day = out / days
    monthly_out = round(per_day * MONTH_DAYS, 2)
    cover = max(total_cash, 0.0)
    days_cover = math.floor(cover / per_day)
    band = next((t for t in snapshot.targets if t.unit == "x" and "runway" in t.label.lower()), None)
    return Runway(unit="days" if days_cover < SHORT_DAYS else "months", days_cover=days_cover,
                  months=round(cover / monthly_out, 1), daily_out=round(per_day, 2), monthly_out=monthly_out,
                  days=days, since=since, through=through, stale=(today - through).days > STALE_DAYS,
                  moved=round(sum(-rows[o].amount for o, _ in pairs), 2), moved_count=len(pairs),
                  aim=band.target if band else None, low=band.low if band else None,
                  high=band.high if band else None)


def _month_end(day: dt.date) -> dt.date:
    return (day.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)


def flows_of(rows: list[Transaction], pairs: list[tuple[int, int]], today: dt.date) -> list[MonthFlow]:
    """Money in and out per calendar month over the cash accounts' rows, moves between them left out, ascending; each
    month with the days the window covers (from the oldest row, to the view's day)."""
    moved_ids = {k for pair in pairs for k in pair}
    outs = {o for o, _ in pairs}
    by_month: dict[str, list[float]] = {}
    for k, r in enumerate(rows):
        totals = by_month.setdefault(r.date.strftime("%Y-%m"), [0.0, 0.0, 0.0])
        if k in outs:
            totals[2] -= r.amount
        elif k in moved_ids:
            continue
        elif r.amount > 0:
            totals[0] += r.amount
        else:
            totals[1] -= r.amount
    since = min((r.date for r in rows), default=today)
    flows = []
    for month, (money_in, money_out, moved) in sorted(by_month.items()):
        first = dt.date.fromisoformat(f"{month}-01")
        last = _month_end(first)
        start, end = max(first, since), max(min(last, today), since)
        flows.append(MonthFlow(month=month, money_in=round(money_in, 2), money_out=round(money_out, 2),
                               net=round(money_in - money_out, 2), moved=round(moved, 2), start=start, end=end,
                               days=(end - start).days + 1, partial=(start, end) != (first, last)))
    return flows


def coverage_text(runway: Runway) -> str:
    """"4 days", "1 day" or "6.3 months": days under SHORT_DAYS, months from it."""
    if runway.unit == "months":
        return f"{runway.months:.1f} months"
    return f"{runway.days_cover} day{'' if runway.days_cover == 1 else 's'}"


def reserves_summary(net: float, runway: Runway | None) -> str:
    text = (f"{_money_text(net)} in cash after recorded debts." if net >= 0
            else f"Recorded debts are {_money_text(-net)} more than your cash.")
    if runway is not None:
        last = ("it would not last a day" if runway.days_cover == 0
                else f"it would last about {coverage_text(runway)}")
        text += (f" Leaving aside moves between your own accounts, money has left your cash at about "
                 f"{_money_text(runway.daily_out)} a day these {runway.days} days: {last}.")
    return text


def reserves_view(snapshot: Snapshot, profile: Profile, now: dt.datetime) -> ReservesView:
    today = now.astimezone(profile.tz).date()
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
    lines = [(a.as_of.date(), a.name) for a in snapshot.accounts if a.category in ("cash", "debt")]
    totals = Totals(cash=total_cash, owed=total_owed, net=round(total_cash - total_owed, 2),
                    utilization_pct=utilization, cash_count=len(cash), debt_count=len(debts),
                    limited_count=len(limited), oldest_as_of=min((d for d, _ in lines), default=None),
                    newest_as_of=max((d for d, _ in lines), default=None),
                    stale=[name for day, name in sorted(lines) if (today - day).days > STALE_DAYS])
    # what of the debt and the cash has a rate on record: every interest figure below covers that part only
    owing = [d for d in debts if d.owed > 0]
    owed = round(sum(d.owed for d in owing), 2)
    rated_owed = round(sum(d.owed for d in owing if d.rate_pct is not None), 2)
    rates = Rates(owed=owed, rated_owed=rated_owed,
                  rated_owed_pct=round(rated_owed / owed * 100, 2) if owed > 0 else None,
                  unrated=[d.name for d in owing if d.rate_pct is None], cash=total_cash,
                  rated_cash=round(sum(c.value for c in cash if c.rate_pct is not None), 2)) if cash or debts else None

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
    pairs = moves_of(rows, cash_accounts)
    runway = runway_of(rows, pairs, total_cash, snapshot, today)
    return ReservesView(as_of=now, today=today, summary=reserves_summary(totals.net, runway), runway=runway,
                        flows=flows_of(rows, pairs, today), cash=cash, debts=debts, totals=totals, spread=spread,
                        rates=rates)
